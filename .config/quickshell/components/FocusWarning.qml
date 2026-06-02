import Quickshell
import Quickshell.Wayland
import QtQuick
import QtQuick.Layouts

PanelWindow {
    id: warningWindow
    visible: root.focusWarningVisible
    screen: Quickshell.screens[0]

    // Flotante en el medio usando márgenes
    exclusionMode: ExclusionMode.Ignore
    anchors { top: true; left: true; right: true }
    margins {
        left: screen.width / 2 - 200
        right: screen.width / 2 - 200
        top: screen.height / 2 - 60
    }
    height: 120

    WlrLayershell.layer: WlrLayer.Overlay
    
    color: "transparent"

    Rectangle {
        anchors.fill: parent
        color: Qt.rgba(0.05, 0.05, 0.05, 0.95)
        radius: 20
        border.width: 2
        border.color: "#8be9fd"

        RowLayout {
            anchors.centerIn: parent
            spacing: 20

            Text {
                text: "󱐌"
                color: "#ffb86c"
                font.pixelSize: 48
                font.family: "JetBrainsMono Nerd Font"
            }

            ColumnLayout {
                spacing: 2
                Text {
                    text: "APP BLOQUEADA"
                    color: "#8be9fd"
                    font.pixelSize: 18
                    font.bold: true
                    font.family: "JetBrainsMono Nerd Font"
                }
                Text {
                    id: appNameText
                    text: "Vuelve a concentrarte..."
                    color: "white"
                    font.pixelSize: 14
                    font.family: "JetBrainsMono Nerd Font"
                    opacity: 0.8
                }
            }
        }
    }

    // Auto cerrar después de 3 segundos
    Timer {
        id: autoCloseTimer
        interval: 3000
        running: warningWindow.visible
        onTriggered: root.focusWarningVisible = false
    }
}
