// My apps: what's installed, with Remove.
import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    readonly property var s: hub.strings
    readonly property var ctl: hub.installed

    title: s["nav.installed"]

    ListView {
        id: list
        model: page.ctl.model
        reuseItems: true
        delegate: AppDelegate {
            appsModel: page.ctl.model
        }

        Kirigami.PlaceholderMessage {
            anchors.centerIn: parent
            width: parent.width - Kirigami.Units.gridUnit * 4
            visible: list.count === 0 && !page.ctl.loading
            icon.name: "view-list-icons"
            text: page.ctl.message
        }
        QQC2.BusyIndicator {
            anchors.centerIn: parent
            running: page.ctl.loading
            visible: running
        }
    }

    Component.onCompleted: ctl.reload()
}
