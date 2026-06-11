import Quickshell
import Quickshell.Wayland
import Quickshell.Io
import Quickshell.Services.Pipewire
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: audioSelector
    
    property bool showing: false
    property string mainMonitor: ""
    property var colors
    
    screen: Quickshell.screens.find(s => s.name === mainMonitor) ?? Quickshell.screens[0]
    
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "audio-selector"
    
    // Do not reserve screen space (floating)
    exclusionMode: ExclusionMode.Ignore
    
    anchors {
        top: true
        right: true
    }
    
    // Position near the top-right where the volume sliders are
    margins.top: root.topPanelVisible ? 50 : 10
    margins.right: 20
    
    width: 400
    // Use implicitHeight to avoid deprecation warning and for cleaner layout
    implicitHeight: 350
    
    color: "transparent"
    
    // Control window visibility
    visible: showing || container.opacity > 0
    
    // Colors from theme or defaults
    readonly property color clrBg:      "#1a1a1a" // Grayer background
    readonly property color clrBorder:  "#333333" // More visible gray border
    readonly property color clrText:    "#d0d0d0" // Slightly softer gray text
    readonly property color clrAccent:  colors ? colors.primary : "#89b4fa"
    readonly property color clrSurface: "#242424" // Surface gray for items
    
    // ── Filtrado de dispositivos ────────────────────────────────────────
    readonly property var filteredDevices: {
        if (!Pipewire.ready) return []
        return Pipewire.nodes.values.filter(function(node) {
            // Sinks que no son streams (dispositivos físicos)
            if (!node.isSink || node.isStream) return false
            
            var desc = (node.description || "").toLowerCase()
            var name = (node.name || "").toLowerCase()
            
            // Si el filtrado es muy agresivo, mostramos todo lo que sea Sink real
            // Pero intentamos priorizar lo que el usuario mencionó
            var matchesKeyword = desc.includes("ryzen") || 
                               desc.includes("usb") || 
                               desc.includes("baffin") || 
                               desc.includes("hdmi") ||
                               desc.includes("stereo") ||
                               desc.includes("analog")
            
            return matchesKeyword
        })
    }

    Rectangle {
        id: container
        anchors.fill: parent
        color: audioSelector.clrBg
        radius: 16
        border.color: audioSelector.clrBorder
        border.width: 1

        // Fade animation
        opacity: showing ? 1 : 0
        Behavior on opacity {
            NumberAnimation { duration: 250; easing.type: Easing.OutCubic }
        }

        // Scale animation to make it "pop out"
        scale: showing ? 1 : 0.8
        transformOrigin: Item.TopRight
        Behavior on scale {
            NumberAnimation { duration: 250; easing.type: Easing.OutBack }
        }
        
        // Shadow effect
        layer.enabled: true
        layer.effect: DropShadow {
            transparentBorder: true
            color: "#b0000000"
            radius: 25
            samples: 41
            verticalOffset: 12
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            
            RowLayout {
                Layout.fillWidth: true
                Text {
                    text: "\ue44a" // speakerHigh icon
                    font.family: "Phosphor-Bold"
                    font.pixelSize: 22
                    color: audioSelector.clrAccent
                }
                Text {
                    text: "Salida de Audio"
                    color: audioSelector.clrText
                    font.bold: true
                    font.pixelSize: 18
                    Layout.fillWidth: true
                }
                IconButton {
                    iconText: "\ue272" // close icon
                    onClicked: root.audioSelectorVisible = false
                }
            }
            
            Rectangle {
                Layout.fillWidth: true
                height: 1
                color: audioSelector.clrBorder
            }
            
            ListView {
                id: deviceList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                model: audioSelector.filteredDevices
                spacing: 6
                
                delegate: ItemDelegate {
                    width: deviceList.width
                    height: 52
                    
                    // Track changes in the node properties
                    PwObjectTracker {
                        objects: [modelData]
                    }
                    
                    readonly property bool isDefault: {
                        // Comprobación robusta del dispositivo por defecto
                        if (!Pipewire.defaultAudioSink) return false
                        return Pipewire.defaultAudioSink === modelData || Pipewire.defaultAudioSink.id === modelData.id
                    }
                    
                    background: Rectangle {
                        color: hovered ? "#2a2a2a" : (isDefault ? Qt.rgba(audioSelector.clrAccent.r, audioSelector.clrAccent.g, audioSelector.clrAccent.b, 0.15) : audioSelector.clrSurface)
                        radius: 12
                        border.width: isDefault ? 2 : 0
                        border.color: audioSelector.clrAccent
                    }
                    
                    contentItem: RowLayout {
                        spacing: 12
                        Rectangle {
                            width: 10; height: 10; radius: 5
                            color: audioSelector.clrAccent
                            visible: isDefault
                            Layout.leftMargin: 8
                        }
                        Text {
                            text: modelData.description || modelData.name || "Unknown Device"
                            color: isDefault ? "#ffffff" : audioSelector.clrText
                            font.pixelSize: 14
                            font.bold: isDefault
                            Layout.fillWidth: true
                            elide: Text.ElideRight
                        }
                    }
                    
                    onClicked: {
                        console.log("Intentando cambiar audio a ID: " + modelData.id)
                        // Usamos wpctl set-default que es el método más fiable en la mayoría de distros
                        setSinkProc.command = ["wpctl", "set-default", modelData.id.toString()]
                        setSinkProc.running = true
                    }
                }
            }
        }
    }
    
    Process {
        id: setSinkProc
        onExited: {
            console.log("wpctl set-default finalizado")
            // Forzamos un refresco visual de la lista
            deviceList.forceLayout()
        }
    }
    
    // Internal IconButton component
    component IconButton: Rectangle {
        property string iconText: ""
        signal clicked
        
        width: 32; height: 32; radius: 8
        color: iconBtnMouse.containsMouse ? Qt.rgba(1,1,1,0.1) : "transparent"
        
        Text {
            anchors.centerIn: parent
            text: parent.iconText
            font.family: "Phosphor-Bold"
            font.pixelSize: 16
            color: audioSelector.clrText
        }
        
        MouseArea {
            id: iconBtnMouse
            anchors.fill: parent
            hoverEnabled: true
            onClicked: parent.clicked()
        }
    }
}
