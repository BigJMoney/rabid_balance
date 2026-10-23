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
    commandEvent.player.persistentData.putInt('rb_horde_threat', 10)
}

// Command to set second big horde threat increase
function setHordeThreat2(commandEvent) {
    commandEvent.player.persistentData.putInt('rb_horde_threat', 20)
}

// Command to reset all horde threat
function resetHordeThreat(commandEvent) {
    commandEvent.player.persistentData.putInt('rb_horde_threat', 0)
}

// Command to report horde threat
function getHordeThreat(commandEvent) {
    const threat = commandEvent.player.persistentData.getInt('rb_horde_threat')
    commandEvent.player.tell(`Current horde threat: ${threat}`)
}


// Register login callbacks
PlayerEvents.loggedIn(initHordeThreat)

// Register command callbacks
ServerEvents.basicPublicCommand('horde_threat_1', setHordeThreat1)
ServerEvents.basicPublicCommand('horde_threat_2', setHordeThreat2)
ServerEvents.basicPublicCommand('horde_threat_reset', resetHordeThreat)
ServerEvents.basicPublicCommand('horde_threat_get', getHordeThreat)
