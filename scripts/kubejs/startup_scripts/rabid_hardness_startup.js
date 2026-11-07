// priority: -10000
// Install in kubejs/startup_scripts/. Run after other block-stat modifications.
(function () {
    function read(path) { return JSON.parse(JsonIO.readString(path)); }
    function fail(message) { throw new Error("[rabid hardness] " + message); }

    BlockEvents.modification(function (event) {
        var folder = "kubejs/config/rabid_hardness";
        var Empty = Java.loadClass("net.minecraft.world.level.EmptyBlockGetter");
        var javaIds = Block.getTypeList().toArray();
        var baseline = {};
        var categories = Object.create(null);
        var session;
        var config;
        var saved;
        var ids;
        var block;
        var state;
        var category;
        var id;
        var i;
        if (global.rabidHardnessSessionJson != null) { fail("Fully restart instead of reloading startup scripts"); }
        // Capture original values once, before this script changes any states.
        for (i = 0; i < javaIds.length; i++) {
            id = String(javaIds[i]);
            block = Block.getBlock(id);
            state = block.defaultBlockState();
            baseline[id] = {
                hardness: Number(state.getDestroySpeed(Empty.INSTANCE, BlockPos.ZERO)),
                protected: Boolean(state.isAir()) || Boolean(state.liquid())
            };
            if (!isFinite(baseline[id].hardness)) { fail("Cannot read hardness for " + id); }
            baseline[id].protected = baseline[id].protected || baseline[id].hardness < 0;
        }
        session = { baseline: baseline, active: null };
        global.rabidHardnessSessionJson = JSON.stringify(session);
        config = read(folder + ".json");
        if (!config || config.version !== 1 || !Array.isArray(config.categories) ||
                config.applyGenerated !== undefined && typeof config.applyGenerated !== "boolean" ||
                config.allowProtectedBlocks !== undefined && typeof config.allowProtectedBlocks !== "boolean") { fail("Invalid config"); }
        if (config.applyGenerated !== true) {
            console.info("[rabid hardness] Generation-only mode; no blocks or hardness tags changed.");
            return;
        }
        saved = read(folder + ".generated.json");
        if (saved === null) { console.info("[rabid hardness] No generated assignments yet; generate, then fully restart."); return; }
        if (saved.version !== 2 || !saved.assignments || typeof saved.assignments !== "object" || Array.isArray(saved.assignments) ||
                JSON.stringify(saved.rules) !== JSON.stringify({ allowProtectedBlocks: config.allowProtectedBlocks === true, categories: config.categories })) {
            fail("Generated assignments are stale/invalid; run /hardness generate and fully restart");
        }
        for (i = 0; i < config.categories.length; i++) { categories[config.categories[i].name] = config.categories[i]; }
        ids = Object.keys(saved.assignments);
        // Check all IDs/categories before applying any values. No classification replay.
        for (i = 0; i < ids.length; i++) {
            category = categories[saved.assignments[ids[i]]];
            if (!Object.prototype.hasOwnProperty.call(baseline, ids[i]) || typeof saved.assignments[ids[i]] !== "string" || !category ||
                    (!config.allowProtectedBlocks && baseline[ids[i]].protected)) { fail("Invalid assignment: " + ids[i]); }
        }
        for (i = 0; i < ids.length; i++) {
            category = categories[saved.assignments[ids[i]]];
            event.modify(ids[i], function (properties) {
                if (category.hardness !== undefined) { properties.setDestroySpeed(category.hardness); }
                if (category.blastResistance !== undefined) { properties.setExplosionResistance(category.blastResistance); }
            });
        }
        session.active = saved;
        global.rabidHardnessSessionJson = JSON.stringify(session);
        console.info("[rabid hardness] Applied " + ids.length + " assignment(s).");
    });
}());
