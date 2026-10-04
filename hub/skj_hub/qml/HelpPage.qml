// Help & safety: "don't be scared of commands" + red flags (Notion plan).
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    readonly property var s: hub.strings

    title: s["help.title"]

    actions: [
        Kirigami.Action {
            text: page.s["help.report"]
            icon.name: "tools-report-bug"
            onTriggered: Qt.openUrlExternally("https://github.com/SKJ-Technology/skj-os-ez/issues")
        }
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Repeater {
            model: [
                { "title": page.s["help.commands_title"], "body": page.s["help.commands"] },
                { "title": page.s["help.flags_title"], "body": page.s["help.flags"] }
            ]
            Kirigami.Card {
                required property var modelData
                Layout.fillWidth: true
                header: Kirigami.Heading {
                    text: modelData.title
                    level: 3
                    wrapMode: Text.WordWrap
                }
                contentItem: QQC2.Label {
                    text: modelData.body
                    wrapMode: Text.WordWrap
                }
            }
        }
    }
}
