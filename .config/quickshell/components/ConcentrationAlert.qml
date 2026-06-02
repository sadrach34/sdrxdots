import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import QtQuick
import QtQuick.Layouts
import "./dashboard"

PanelWindow {
    id: alertWindow
    visible: root.concentrationAlertVisible
    screen: Quickshell.screens[0]
    
    // Hacerla flotante (no reserva espacio en pantalla)
    exclusionMode: ExclusionMode.Ignore

    // Centrar arriba usando márgenes (mitad de pantalla)
    anchors { top: true; left: true; right: true }
    margins {
        left: screen.width / 4
        right: screen.width / 4
        top: 20
    }
    height: 140

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus: root.concentrationAlertVisible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    
    color: "transparent"

    DashTheme { id: theme }

    // Item interno para manejar eventos de teclado y centrado
    Item {
        anchors.fill: parent
        focus: alertWindow.visible

        Keys.onPressed: function(event) {
            event.accepted = true;
        }

        Rectangle {
            anchors.fill: parent
            color: "#0a0a0a"
            radius: 20
            border.width: 2
            border.color: blinkAnim.running ? "#8be9fd" : "#44475a"

            RowLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 30

                // ── 1. Reloj Celeste Parpadeante ──
                RowLayout {
                    Layout.alignment: Qt.AlignVCenter
                    spacing: 20

                    ColumnLayout {
                        spacing: 0

                        Text {
                            id: blinkClock
                            text: "00:00"
                            color: "#8be9fd"
                            font.pixelSize: 52
                            font.bold: true
                            font.family: "JetBrainsMono Nerd Font"
                            
                            SequentialAnimation on opacity {
                                id: blinkAnim
                                loops: Animation.Infinite
                                running: alertWindow.visible
                                NumberAnimation { from: 1.0; to: 0.2; duration: 500; easing.type: Easing.InOutSine }
                                NumberAnimation { from: 0.2; to: 1.0; duration: 500; easing.type: Easing.InOutSine }
                            }

                            Timer {
                                interval: 1000; running: true; repeat: true; triggeredOnStart: true
                                onTriggered: {
                                    var d = new Date()
                                    blinkClock.text = d.toLocaleTimeString(Qt.locale(), "HH:mm")
                                }
                            }
                        }
                        
                        Text {
                            text: "TIEMPO AGOTADO"
                            color: "#8be9fd"
                            font.pixelSize: 10
                            font.bold: true
                            Layout.alignment: Qt.AlignHCenter
                        }
                    }

                    // Botón de Campana (Mute)
                    Rectangle {
                        width: 44; height: 44; radius: 22
                        color: root.concentrationMuted ? Qt.rgba(0.54, 0.91, 0.99, 0.2) : "#1a1a1a"
                        border.width: 1; border.color: root.concentrationMuted ? "#8be9fd" : "#333"
                        
                        Text {
                            anchors.centerIn: parent
                            text: root.concentrationMuted ? "\uf1f6" : "\uf0f3"
                            font.family: "JetBrainsMono Nerd Font"
                            font.pixelSize: 24
                            color: root.concentrationMuted ? "#8be9fd" : "white"
                        }

                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.concentrationMuted = !root.concentrationMuted
                        }
                    }
                }

                // Separador
                Rectangle { width: 1; Layout.fillHeight: true; color: "#222" }

                // ── 2. Mensaje y Botón ──
                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        text: "¡Sesión finalizada!"
                        color: "white"
                        font.pixelSize: 16
                        font.bold: true
                    }

                    // Botón Aceptar
                    Rectangle {
                        Layout.fillWidth: true
                        height: 44; radius: 10
                        color: acceptMa.containsMouse ? "#50fa7b" : "#1a1a1a"
                        border.width: 1; border.color: "#333"
                        
                        Text {
                            anchors.centerIn: parent
                            text: "ACEPTAR"
                            color: acceptMa.containsMouse ? "black" : "white"
                            font.pixelSize: 14; font.bold: true
                        }

                        MouseArea {
                            id: acceptMa
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                root.concentrationAlertVisible = false
                                alarmProc.running = false
                            }
                        }
                    }
                }
            }
        }
    }

    Process {
        id: alarmProc
        running: alertWindow.visible && !root.concentrationMuted
        command: ["bash", "-c", "while true; do paplay /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga 2>/dev/null || (command -v mpv >/dev/null && mpv --no-video /usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga) || sleep 5; done"]
    }
}
