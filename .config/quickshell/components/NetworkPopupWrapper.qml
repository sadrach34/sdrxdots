import Quickshell
import Quickshell.Wayland
import QtQuick
import QtQuick.Layouts
import QtQuick.Controls
import Qt5Compat.GraphicalEffects
import "./network"

PanelWindow {
    id: networkPopupWrapper

    property bool showing: false
    property string mainMonitor: ""
    property string activeMode: "wifi"

    screen: Quickshell.screens.find(s => s.name === mainMonitor) ?? Quickshell.screens[0]

    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "network-popup"

    exclusionMode: ExclusionMode.Ignore
    focusable: true
    
    WlrLayershell.keyboardFocus: showing ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

    anchors {
        top: true
        right: true
    }
    
    // Position it nicely on the right side of the screen
    margins.top: root.topPanelVisible ? 55 : 42
    margins.right: 20
    
    width: 900
    implicitHeight: 700
    color: "transparent"

    visible: showing || container.opacity > 0

    Rectangle {
        id: container
        anchors.fill: parent
        color: "transparent"

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
        
        layer.enabled: true
        layer.effect: DropShadow {
            transparentBorder: true
            color: "#b0000000"
            radius: 25
            samples: 41
            verticalOffset: 12
        }

        NetworkPopup {
            id: innerPopup
            anchors.fill: parent
            activeMode: networkPopupWrapper.activeMode
            isWindowVisible: networkPopupWrapper.showing
        }
    }
}
