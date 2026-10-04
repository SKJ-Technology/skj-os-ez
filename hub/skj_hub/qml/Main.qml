// SKJ Hub main window: Kirigami, like Discover and System Settings.
// `hub` is the Python Bridge (ui/bridge.py); `hub.strings` holds every text.
import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root

    readonly property var s: hub.strings
    property string currentPage: ""

    title: s["app.title"]
    width: Kirigami.Units.gridUnit * 58
    height: Kirigami.Units.gridUnit * 38
    minimumWidth: Kirigami.Units.gridUnit * 34
    minimumHeight: Kirigami.Units.gridUnit * 24

    function showPage(name) {
        if (name === currentPage || !pages[name]) {
            return
        }
        currentPage = name
        pageStack.clear()
        pageStack.push(pages[name])
    }

    // Components (not URLs): the page stack creates them inside the scene
    readonly property var pages: ({
        "start": startPageComponent,
        "apps": appsPageComponent,
        "installed": installedPageComponent,
        "updates": updatesPageComponent,
        "help": helpPageComponent
    })

    Component { id: startPageComponent; StartPage {} }
    Component { id: appsPageComponent; AppsPage {} }
    Component { id: installedPageComponent; InstalledPage {} }
    Component { id: updatesPageComponent; UpdatesPage {} }
    Component { id: helpPageComponent; HelpPage {} }

    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.ToolBar
    pageStack.columnView.columnResizeMode: Kirigami.ColumnView.SingleColumn

    globalDrawer: Kirigami.GlobalDrawer {
        modal: false
        collapsible: false
        showHeaderWhenCollapsed: false
        width: Kirigami.Units.gridUnit * 14
        header: Kirigami.AbstractApplicationHeader {
            contentItem: Kirigami.Heading {
                text: root.s["app.title"]
                level: 2
                leftPadding: Kirigami.Units.largeSpacing
                verticalAlignment: Text.AlignVCenter
            }
        }
        actions: [
            Kirigami.Action {
                text: root.s["nav.start"]
                icon.name: "go-home"
                checked: root.currentPage === "start"
                onTriggered: root.showPage("start")
            },
            Kirigami.Action {
                text: root.s["nav.apps"]
                icon.name: "system-software-install"
                checked: root.currentPage === "apps"
                onTriggered: root.showPage("apps")
            },
            Kirigami.Action {
                text: root.s["nav.installed"]
                icon.name: "view-list-icons"
                checked: root.currentPage === "installed"
                onTriggered: root.showPage("installed")
            },
            Kirigami.Action {
                text: root.s["nav.updates"]
                icon.name: "system-software-update"
                checked: root.currentPage === "updates"
                onTriggered: root.showPage("updates")
            },
            Kirigami.Action {
                text: root.s["nav.help"]
                icon.name: "help-about"
                checked: root.currentPage === "help"
                onTriggered: root.showPage("help")
            }
        ]
    }

    Component.onCompleted: showPage(startPage)
}
