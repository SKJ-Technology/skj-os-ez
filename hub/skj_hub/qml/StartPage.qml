// Start: hello, two big buttons, and whether updates are waiting.
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    readonly property var s: hub.strings

    title: s["nav.start"]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: hub.demo
            type: Kirigami.MessageType.Information
            text: page.s["start.demo"]
        }
        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: !hub.supported
            type: Kirigami.MessageType.Warning
            text: page.s["start.unsupported"]
        }

        Kirigami.Icon {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: Kirigami.Units.gridUnit
            Layout.preferredWidth: Kirigami.Units.iconSizes.enormous
            Layout.preferredHeight: Kirigami.Units.iconSizes.enormous
            source: "skj-logo-icon"
            fallback: "start-here"
        }
        Kirigami.Heading {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: page.s["start.hello"]
            level: 1
            wrapMode: Text.WordWrap
        }
        QQC2.Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: page.s["start.sub"]
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: Kirigami.Units.largeSpacing
            spacing: Kirigami.Units.largeSpacing

            QQC2.Button {
                text: page.s["start.find_apps"]
                icon.name: "system-software-install"
                highlighted: true
                onClicked: applicationWindow().showPage("apps")
            }
            QQC2.Button {
                text: page.s["start.check_updates"]
                icon.name: "system-software-update"
                onClicked: applicationWindow().showPage("updates")
            }
        }

        QQC2.Label {
            Layout.fillWidth: true
            Layout.topMargin: Kirigami.Units.largeSpacing
            horizontalAlignment: Text.AlignHCenter
            text: hub.updates.summary
            wrapMode: Text.WordWrap
            opacity: 0.7
        }
    }

    Component.onCompleted: {
        if (hub.updates.state === "checking") {
            hub.updates.check()
        }
    }
}
