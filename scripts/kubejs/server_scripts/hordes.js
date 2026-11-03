/**
 * Code for The Hordes
 *
 */

// Initialize every player's horde threat to 0
function initHordeThreat(loginEvent) {
    const data = loginEvent.player.persistentData

    if (!data.contains('rb_horde_threat')) {
        data.putInt('rb_horde_threat', 0)
    }
}

// Command to set first big horde threat increase
function setHordeThreat1(commandEvent) {
    commandEvent.source.player.persistentData.putInt('rb_horde_threat', 10)
    return 1
}

// Command to set second big horde threat increase
function setHordeThreat2(commandEvent) {
    commandEvent.source.player.persistentData.putInt('rb_horde_threat', 20)
    return 1
}

// Command to reset all horde threat
function resetHordeThreat(commandEvent) {
    commandEvent.source.player.persistentData.putInt('rb_horde_threat', 0)
    return 1
}

// Command to report horde threat
function getHordeThreat(commandEvent) {
    const threat = commandEvent.source.player.persistentData.getInt('rb_horde_threat')
    commandEvent.source.player.tell(`Current horde threat: ${threat}`)
    return 1
}

// Register commands with operator permissions
function registerHordeCommands(registryEvent) {
    const Commands = registryEvent.commands

    registryEvent.register(
        Commands.literal('horde_threat_1')
            .requires(source => source.hasPermission(2))
            .executes(setHordeThreat1)
    )

    registryEvent.register(
        Commands.literal('horde_threat_2')
            .requires(source => source.hasPermission(2))
            .executes(setHordeThreat2)
    )

    registryEvent.register(
        Commands.literal('horde_threat_reset')
            .requires(source => source.hasPermission(2))
            .executes(resetHordeThreat)
    )

    registryEvent.register(
        Commands.literal('horde_threat_get')
            .requires(source => source.hasPermission(2))
            .executes(getHordeThreat)
    )
}

// Register login callbacks
PlayerEvents.loggedIn(initHordeThreat)

// Register command callbacks
ServerEvents.commandRegistry(registerHordeCommands)
