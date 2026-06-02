import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import "../dashboard"
import "./"

Item {
    id: focusRoot
    anchors.fill: parent

    property int totalTime: 30 * 60
    property int timeLeft: 30 * 60 
    property bool running: false
    property bool zenMode: true // Nuevo: Desactiva animaciones/blur
    property var theme
    
    property double endTimestamp: 0

    onRunningChanged: {
        if (running) {
            dndProc.command = ["swaync-client", "-d", "on"]
            dndProc.running = true
        } else {
            dndProc.command = ["swaync-client", "-d", "off"]
            dndProc.running = true
        }
        saveState()
    }

    function formatTime(seconds) {
        var mins = Math.floor(seconds / 60)
        var secs = seconds % 60
        return (mins < 10 ? "0" : "") + mins + ":" + (secs < 10 ? "0" : "") + secs
    }

    function adjustTime(deltaSeconds) {
        timeLeft = Math.max(0, timeLeft + deltaSeconds)
        totalTime = timeLeft
        if (running) {
            endTimestamp = Date.now() + (timeLeft * 1000)
        }
        saveState()
        canvas.requestPaint()
    }

    function saveState() {
        var runBit = running ? "1" : "0"
        var zenBit = zenMode ? "1" : "0"
        stateWriter.command = ["bash", "-c", "echo '" + endTimestamp + "|" + runBit + "|" + totalTime + "|" + zenBit + "' > " + Quickshell.env("HOME") + "/.cache/quickshell/focus_timer.state"]
        stateWriter.running = true
    }

    function loadState() {
        var raw = stateReader.text().trim()
        if (!raw) return
        
        var parts = raw.split("|")
        if (parts.length < 3) return
        
        var savedEnd = parseFloat(parts[0])
        var savedRun = parts[1] === "1"
        var savedTotal = parseInt(parts[2])
        var savedZen = parts.length >= 4 ? (parts[3] === "1") : true
        
        totalTime = savedTotal
        zenMode = savedZen
        
        if (savedRun) {
            var now = Date.now()
            if (savedEnd > now) {
                endTimestamp = savedEnd
                timeLeft = Math.ceil((savedEnd - now) / 1000)
                running = true
            } else {
                timeLeft = 0
                running = false
                root.concentrationAlertVisible = true
            }
        } else {
            timeLeft = savedTotal
            running = false
        }
        canvas.requestPaint()
    }

    FileView {
        id: stateReader
        path: Quickshell.env("HOME") + "/.cache/quickshell/focus_timer.state"
    }

    Process { id: stateWriter }
    Process { id: daemonStarter }
    Process { id: dndProc }

    Component.onCompleted: {
        loadState()
        daemonStarter.command = ["bash", "-c", "pgrep -f focus-daemon.sh >/dev/null || " + Quickshell.env("HOME") + "/.config/quickshell/scripts/bash/focus-daemon.sh &"]
        daemonStarter.running = true
    }

    Timer {
        id: countTimer
        interval: 1000
        running: focusRoot.running && focusRoot.timeLeft > 0
        repeat: true
        onTriggered: {
            var now = Date.now()
            if (endTimestamp > now) {
                focusRoot.timeLeft = Math.ceil((endTimestamp - now) / 1000)
            } else {
                focusRoot.timeLeft = 0
                focusRoot.running = false
                root.concentrationAlertVisible = true
                saveState()
            }
            canvas.requestPaint()
        }
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 15
        spacing: 15

        Rectangle {
            Layout.preferredWidth: 260
            Layout.fillHeight: true
            color: "#0a0a0a"
            radius: 16
            border.width: 1
            border.color: "#1a1a1a"
            clip: true
            FullPlayer {
                anchors.fill: parent
                anchors.margins: 10
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#0a0a0a"
            radius: 16
            border.width: 1
            border.color: "#1a1a1a"

            ColumnLayout {
                anchors.centerIn: parent
                spacing: 15

                Text {
                    text: "CONCENTRACIÓN"
                    color: theme.accent
                    font.pixelSize: 16
                    font.bold: true
                    font.family: "JetBrainsMono Nerd Font"
                    Layout.alignment: Qt.AlignHCenter
                    opacity: 0.6
                }

                Item {
                    Layout.preferredWidth: 260
                    Layout.preferredHeight: 260
                    Layout.alignment: Qt.AlignHCenter

                    Canvas {
                        id: canvas
                        anchors.fill: parent
                        onPaint: {
                            var ctx = getContext("2d")
                            var x = width / 2
                            var y = height / 2
                            var radius = Math.min(width, height) / 2 - 10
                            var progress = focusRoot.timeLeft / focusRoot.totalTime
                            if (focusRoot.totalTime === 0) progress = 0
                            ctx.clearRect(0, 0, width, height)
                            ctx.beginPath()
                            ctx.strokeStyle = "#1a1a1a"
                            ctx.lineWidth = 12
                            ctx.arc(x, y, radius, 0, 2 * Math.PI)
                            ctx.stroke()
                            ctx.beginPath()
                            ctx.strokeStyle = focusRoot.running ? "#50fa7b" : "#8be9fd"
                            ctx.lineWidth = 12
                            ctx.lineCap = "round"
                            ctx.arc(x, y, radius, -Math.PI / 2, -Math.PI / 2 + (2 * Math.PI * progress))
                            ctx.stroke()
                            ctx.strokeStyle = "#333"
                            ctx.lineWidth = 2
                            for (var i = 0; i < 12; i++) {
                                var angle = (i * 30) * Math.PI / 180
                                ctx.beginPath()
                                ctx.moveTo(x + (radius - 12) * Math.cos(angle), y + (radius - 12) * Math.sin(angle))
                                ctx.lineTo(x + (radius - 5) * Math.cos(angle), y + (radius - 5) * Math.sin(angle))
                                ctx.stroke()
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        text: formatTime(focusRoot.timeLeft)
                        color: "white"
                        font.pixelSize: 52
                        font.bold: true
                        font.family: "JetBrainsMono Nerd Font"
                    }

                    Rectangle {
                        anchors.top: parent.top
                        anchors.right: parent.right
                        width: 36; height: 32; radius: 10
                        color: "transparent"
                        Text {
                            anchors.centerIn: parent
                            text: root.concentrationMuted ? "\uf1f6" : "\uf0f3"
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 22
                            color: root.concentrationMuted ? "#8be9fd" : "#505050"
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.concentrationMuted = !root.concentrationMuted
                        }
                    }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 10
                    Row { 
                        spacing: 4
                        AdjustBtn { text: "-10"; onClicked: adjustTime(-10 * 60) }
                        AdjustBtn { text: "-5";  onClicked: adjustTime(-5 * 60) }
                        AdjustBtn { text: "-1";  onClicked: adjustTime(-1 * 60) }
                    }
                    Row { 
                        spacing: 4
                        AdjustBtn { text: "+1";  onClicked: adjustTime(1 * 60) }
                        AdjustBtn { text: "+5";  onClicked: adjustTime(5 * 60) }
                        AdjustBtn { text: "+10"; onClicked: adjustTime(10 * 60) }
                    }
                }

                RowLayout {
                    Layout.alignment: Qt.AlignHCenter
                    spacing: 20
                    
                    // Zen Mode Toggle
                    Rectangle {
                        width: 50; height: 50; radius: 25
                        color: focusRoot.zenMode ? "#bd93f9" : "#1a1a1a"
                        border.width: 1; border.color: "#333"
                        Text { 
                            anchors.centerIn: parent; 
                            text: "󰄛"; 
                            color: focusRoot.zenMode ? "black" : "white"; 
                            font.pixelSize: 24 
                        }
                        MouseArea { 
                            anchors.fill: parent; 
                            cursorShape: Qt.PointingHandCursor; 
                            onClicked: {
                                focusRoot.zenMode = !focusRoot.zenMode
                                saveState()
                            }
                        }
                    }

                    Rectangle {
                        width: 60; height: 60; radius: 30
                        color: focusRoot.running ? "#ff5555" : "#50fa7b"
                        Text { anchors.centerIn: parent; text: focusRoot.running ? "󰏤" : "󰐊"; color: "black"; font.pixelSize: 28; font.family: "JetBrainsMono Nerd Font" }
                        MouseArea { 
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                focusRoot.running = !focusRoot.running
                                if (focusRoot.running) focusRoot.endTimestamp = Date.now() + (focusRoot.timeLeft * 1000)
                                saveState()
                            }
                        }
                    }
                    
                    Rectangle {
                        width: 50; height: 50; radius: 25
                        color: "#1a1a1a"; border.width: 1; border.color: "#333"
                        Text { anchors.centerIn: parent; text: "󰓛"; color: "white"; font.pixelSize: 20; font.family: "JetBrainsMono Nerd Font" }
                        MouseArea { 
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: { 
                                focusRoot.running = false; focusRoot.timeLeft = 30 * 60; focusRoot.totalTime = 30 * 60; focusRoot.endTimestamp = 0
                                saveState(); canvas.requestPaint() 
                            } 
                        }
                    }
                }
            }
        }

        Rectangle {
            Layout.preferredWidth: 320; Layout.fillHeight: true; color: "#0a0a0a"; radius: 16; border.width: 1; border.color: "#1a1a1a"; clip: true
            AppVolumeWidget { anchors.fill: parent; anchors.margins: 15 }
        }
    }

    component AdjustBtn: Rectangle {
        property string text: ""
        signal clicked()
        width: 40; height: 32; radius: 8
        color: abMa.containsMouse ? "#333" : "#161616"; border.width: 1; border.color: "#222"
        Text { anchors.centerIn: parent; text: parent.text; color: "white"; font.pixelSize: 10; font.bold: true; font.family: "JetBrainsMono Nerd Font" }
        MouseArea { id: abMa; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: parent.clicked() }
    }
}
