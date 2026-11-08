// Install in kubejs/server_scripts/. No common scripts required.
(function () {
    var folder = "kubejs/config/rabid_hardness";
    var exportFolder = "kubejs/export/rabid_hardness";
    var prefix = "rabid:hardness/";
    function read(path) { return JSON.parse(JsonIO.readString(path)); }
    function own(object, key) { return Object.prototype.hasOwnProperty.call(object, key); }
    function fail(message) { throw new Error("[rabid hardness] " + message); }
    function session() {
        if (global.rabidHardnessSessionJson == null) { fail("Missing startup baseline; check startup errors and fully restart"); }
        return JSON.parse(String(global.rabidHardnessSessionJson));
    }
    function textFiles() { return Java.loadClass("org.apache.commons.io.FileUtils"); }
    function formatReport(data) {
        return JSON.stringify(data, null, "\t").replace(
            /^(\t*)"matchedRule": (\{\n[\s\S]*?^\1\})/gm,
            function (match, indent, rule) {
                return indent + '"matchedRule": ' + rule.replace(/\n\t*/g, " ");
            }) + "\n";
    }
    function formatGenerated(data) {
        var text = JSON.stringify({ version: data.version, rules: data.rules, assignments: data.assignments }, null, "\t");
        var ids = Object.keys(data.exclusions);
        var rows = [];
        var names;
        var i;
        var j;
        for (i = 0; i < ids.length; i++) {
            names = [];
            for (j = 0; j < data.exclusions[ids[i]].length; j++) { names.push(JSON.stringify(data.exclusions[ids[i]][j])); }
            rows.push("\t\t" + JSON.stringify(ids[i]) + ": [" + names.join(", ") + "]");
        }
        return text.slice(0, -2) + ",\n\t\"exclusions\": " +
            (rows.length ? "{\n" + rows.join(",\n") + "\n\t}" : "{}") + "\n}\n";
    }
    function write(path, data, inlineExclusions) {
        if (inlineExclusions) {
            textFiles().writeStringToFile(path, formatGenerated(data), "UTF-8");
        } else if (path === exportFolder + ".report.json") {
            textFiles().writeStringToFile(path, formatReport(data), "UTF-8");
        } else {
            JsonIO.write(path, JsonIO.parseRaw(JSON.stringify(data)));
        }
        if (JSON.stringify(read(path)) !== JSON.stringify(data)) { fail("Read-back verification failed: " + path); }
    }

    function generate() {
        var config = read(folder + ".json");
        var current = session();
        var baseline = current.baseline;
        var ids = Object.keys(baseline).sort();
        var availableTags = {};
        var tags = Java.loadClass("net.minecraft.core.registries.BuiltInRegistries").BLOCK.getTagNames().toArray();
        var names = Object.create(null);
        var prepared = [];
        var assignments = {};
        var exclusions = {};
        var report = { assigned: 0, excluded: 0, protected: 0, unmatched: 0, assignments: [], exclusions: [], protectedBlocks: [], conflicts: [] };
        var candidate;
        var old;
        var category;
        var priority;
        var bestPriority;
        var entry;
        var matches;
        var matchDetails;
        var includeIndex;
        var excludeIndex;
        var matchedRule;
        var state;
        var reasons;
        var id;
        var i;
        var j;
        for (i = 0; i < tags.length; i++) { availableTags[String(tags[i].location())] = true; }
        if (!config || config.version !== 1 || !Array.isArray(config.categories) ||
                config.generateOnWorldLoad !== undefined && typeof config.generateOnWorldLoad !== "boolean" ||
                config.allowProtectedBlocks !== undefined && typeof config.allowProtectedBlocks !== "boolean") { fail("Invalid config"); }

        function compile(rule) {
            var regex;
            var members;
            var set = {};
            var keys;
            var k;
            if (!rule || typeof rule !== "object") { fail("Invalid rule"); }
            if (rule.type === "id" || rule.type === "tag") {
                if (typeof rule.value !== "string" || !/^[a-z0-9_.-]+:[a-z0-9/._-]+$/.test(rule.value)) { fail("Use a namespaced ID/tag without #: " + rule.value); }
                if (rule.type === "id") {
                    if (!own(baseline, rule.value)) { fail("Unknown block: " + rule.value); }
                    return function (id) { return id === rule.value; };
                }
                if (rule.value.indexOf(prefix) === 0) { fail("Generated hardness tags cannot be rule inputs"); }
                if (!own(availableTags, rule.value)) { fail("Nonexistent block tag: " + rule.value); }
                members = Block.getTaggedIds(rule.value).toArray();
                for (k = 0; k < members.length; k++) { set[String(members[k])] = true; }
                return function (id) { return own(set, id); };
            }
            if (rule.type === "regex") {
                if (typeof rule.value !== "string" || ["", "i", "m", "im", "mi"].indexOf(rule.flags || "") < 0) { fail("Invalid regex value/flags (only i/m allowed)"); }
                regex = new RegExp(rule.value, rule.flags || "");
                return function (id) { return regex.test(id); };
            }
            if (rule.type !== "hardness") { fail("Unknown rule type: " + rule.type); }
            keys = Object.keys(rule);
            if (keys.length < 2) { fail("Hardness rule needs a comparison"); }
            for (k = 0; k < keys.length; k++) {
                if (keys[k] === "type") { continue; }
                if (["eq", "gt", "gte", "lt", "lte"].indexOf(keys[k]) < 0 || typeof rule[keys[k]] !== "number" || !isFinite(rule[keys[k]])) { fail("Invalid hardness comparison: " + keys[k]); }
            }
            return function (id) {
                var value = baseline[id].hardness;
                return (rule.eq === undefined || value === rule.eq) && (rule.gt === undefined || value > rule.gt) &&
                    (rule.gte === undefined || value >= rule.gte) && (rule.lt === undefined || value < rule.lt) && (rule.lte === undefined || value <= rule.lte);
            };
        }
        function compileList(rules) {
            var compiled = [];
            var k;
            if (!Array.isArray(rules)) { fail("include/exclude must be arrays"); }
            for (k = 0; k < rules.length; k++) { compiled.push(compile(rules[k])); }
            return compiled;
        }
        function firstMatch(rules, id) {
            var k;
            for (k = 0; k < rules.length; k++) { if (rules[k](id)) { return k; } }
            return -1;
        }
        for (i = 0; i < config.categories.length; i++) {
            category = config.categories[i];
            if (!category || typeof category.name !== "string" || !/^[a-z0-9_][a-z0-9_.-]*$/.test(category.name)) { fail("Invalid category name at index " + i); }
            if (own(names, category.name)) { fail("Duplicate category name: " + category.name); }
            names[category.name] = true;
            priority = category.priority === undefined ? 0 : category.priority;
            if (typeof priority !== "number" || !isFinite(priority) || Math.floor(priority) !== priority || Math.abs(priority) > 9007199254740991) {
                fail("Priority must be a safe integer for " + category.name);
            }
            if (category.hardness === undefined && category.blastResistance === undefined) { fail(category.name + " needs hardness and/or blastResistance"); }
            for (j = 0; j < 2; j++) {
                entry = j === 0 ? category.hardness : category.blastResistance;
                if (entry !== undefined && (typeof entry !== "number" || !isFinite(entry) || entry > 3.4028234663852886e38 || entry < 0 && !(j === 0 && entry === -1))) { fail("Invalid output stat for " + category.name); }
            }
            if (!Array.isArray(category.include) || !category.include.length) { fail(category.name + " needs inclusion rules"); }
            prepared.push({ name: category.name, priority: priority, include: compileList(category.include), exclude: compileList(category.exclude === undefined ? [] : category.exclude) });
        }
        for (i = 0; i < ids.length; i++) {
            id = ids[i];
            if (!config.allowProtectedBlocks && baseline[id].protected) {
                report.protected++;
                state = Block.getBlock(id).defaultBlockState();
                reasons = [];
                if (Boolean(state.isAir())) { reasons.push("air"); }
                if (Boolean(state.liquid())) { reasons.push("fluid"); }
                if (baseline[id].hardness < 0) { reasons.push("negative hardness"); }
                report.protectedBlocks.push({ id: id, hardness: baseline[id].hardness, reasons: reasons });
                continue;
            }
            matches = [];
            matchDetails = [];
            bestPriority = -Infinity;
            matchedRule = null;
            for (j = 0; j < prepared.length; j++) {
                entry = prepared[j];
                includeIndex = firstMatch(entry.include, id);
                if (includeIndex < 0) { continue; }
                excludeIndex = firstMatch(entry.exclude, id);
                if (excludeIndex >= 0) {
                    report.excluded++;
                    report.exclusions.push({ id: id, category: entry.name, matchedRule: config.categories[j].exclude[excludeIndex] });
                    if (!own(exclusions, id)) { exclusions[id] = []; }
                    exclusions[id].push(entry.name);
                } else if (entry.priority >= bestPriority) {
                    if (entry.priority > bestPriority) {
                        bestPriority = entry.priority;
                        matches = [];
                        matchDetails = [];
                    }
                    matches.push(entry.name);
                    matchedRule = config.categories[j].include[includeIndex];
                    matchDetails.push({ category: entry.name, matchedRule: matchedRule });
                }
            }
            if (matches.length > 1) { report.conflicts.push({ id: id, priority: bestPriority, matches: matchDetails }); }
            else if (matches.length === 1) {
                assignments[id] = matches[0];
                report.assigned++;
                report.assignments.push({ id: id, category: matches[0], matchedRule: matchedRule });
            }
            else { report.unmatched++; }
        }
        write(exportFolder + ".report.json", report);
        if (report.conflicts.length) {
            for (i = 0; i < report.conflicts.length; i++) {
                entry = report.conflicts[i];
                matches = [];
                for (j = 0; j < entry.matches.length; j++) { matches.push(entry.matches[j].category); }
                console.error("[rabid hardness] Overlap: " + JSON.stringify({ id: entry.id, categories: matches }));
            }
            fail(report.conflicts.length + " overlapping block(s); generated assignments unchanged");
        }
        candidate = { version: 2, rules: { allowProtectedBlocks: config.allowProtectedBlocks === true, categories: config.categories }, assignments: assignments, exclusions: exclusions };
        write(exportFolder + ".candidate.json", candidate, true);
        old = read(folder + ".generated.json");
        if (JSON.stringify(old) !== JSON.stringify(candidate)) {
            if (old !== null) { write(folder + ".backup.json", old); }
            // JsonIO has no atomic rename. A failed final write leaves candidate + backup.
            write(folder + ".generated.json", candidate, true);
        } else if (String(textFiles().readFileToString(folder + ".generated.json", "UTF-8")) !== formatGenerated(candidate)) {
            // Refresh formatting without replacing the previous-data backup.
            write(folder + ".generated.json", candidate, true);
        }
        console.info("[rabid hardness] Generated " + report.assigned + " assignment(s); excluded=" + report.excluded + ", protected=" + report.protected + ", unmatched=" + report.unmatched + ".");
        console.info("[rabid hardness] Active this session: " + (current.active ? Object.keys(current.active.assignments).length : 0) + " assignment(s). Generated output is applied at startup only.");
    }

    ServerEvents.tags("block", function (event) {
        var active = session().active;
        var ids;
        var i;
        if (!active) { return; }
        for (i = 0; i < active.rules.categories.length; i++) { event.removeAll(prefix + active.rules.categories[i].name); }
        ids = Object.keys(active.assignments);
        for (i = 0; i < ids.length; i++) { event.add(prefix + active.assignments[ids[i]], ids[i]); }
    });
    ServerEvents.loaded(function () {
        var config = read(folder + ".json");
        if (!config || config.generateOnWorldLoad !== undefined && typeof config.generateOnWorldLoad !== "boolean") {
            fail("generateOnWorldLoad must be a boolean");
        }
        if (config.generateOnWorldLoad === true) { generate(); }
    });
    ServerEvents.commandRegistry(function (event) {
        event.register(event.commands.literal("hardness").requires(function (source) { return source.hasPermission(2); })
            .then(event.commands.literal("generate").executes(function (context) {
                try { generate(); }
                catch (error) { console.error(String(error)); context.source.sendFailure(Text.of(String(error))); return 0; }
                context.source.sendSuccess(Text.of("Generated. Fully restart to activate; applyGenerated must be true."), false);
                return 1;
            })));
    });
}());
