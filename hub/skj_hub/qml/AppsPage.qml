// Apps: browse a group or search by name.
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    readonly property var s: hub.strings
    readonly property var ctl: hub.apps

    title: s["nav.apps"]

    function refresh() {
        ctl.refresh(search.text, groupBox.currentValue)
    }

    header: QQC2.ToolBar {
        contentItem: GridLayout {
            columns: 2
            columnSpacing: Kirigami.Units.smallSpacing
            rowSpacing: Kirigami.Units.smallSpacing

            Kirigami.SearchField {
                id: search
                Layout.fillWidth: true
                placeholderText: page.s["apps.search"]
                delaySearch: true
                onAccepted: page.refresh()
            }
            QQC2.ComboBox {
                id: groupBox
                model: hub.groups
                textRole: "label"
                valueRole: "key"
                onActivated: page.refresh()
            }
            QQC2.Label {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                text: page.ctl.message
                visible: text !== "" && list.count > 0
                wrapMode: Text.WordWrap
                opacity: 0.7
            }
        }
    }

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
            icon.name: "search"
            text: page.ctl.message
        }
        QQC2.BusyIndicator {
            anchors.centerIn: parent
            running: page.ctl.loading && list.count === 0
            visible: running
        }
    }

    Component.onCompleted: {
        refresh()
        search.forceActiveFocus()
    }
}
