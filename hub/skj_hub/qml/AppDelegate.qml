// One app in a list: icon, name, what it is, where it comes from, one button.
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

QQC2.ItemDelegate {
    id: item

    required property int index
    required property string name
    required property string summary
    required property string source
    required property string iconName
    required property bool installed
    required property bool busy
    required property int progress
    required property string status
    required property string problem
    required property string details
    required property var others

    property var appsModel
    readonly property var s: hub.strings

    width: ListView.view ? ListView.view.width : implicitWidth
    hoverEnabled: true
    down: false

    contentItem: RowLayout {
        spacing: Kirigami.Units.largeSpacing

        Item {
            Layout.preferredWidth: Kirigami.Units.iconSizes.large
            Layout.preferredHeight: Kirigami.Units.iconSizes.large
            Layout.alignment: Qt.AlignTop

            Kirigami.Icon {
                anchors.fill: parent
                source: item.iconName
                visible: item.iconName !== ""
            }
            // no icon: a letter tile in SKJ colours
            Rectangle {
                anchors.fill: parent
                visible: item.iconName === ""
                radius: width * 0.22
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0; color: "#2563eb" }
                    GradientStop { position: 1; color: "#14b8a6" }
                }
                QQC2.Label {
                    anchors.centerIn: parent
                    text: item.name.charAt(0).toUpperCase()
                    color: "white"
                    font.bold: true
                    font.pixelSize: parent.height * 0.5
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Heading {
                Layout.fillWidth: true
                text: item.name
                level: 4
                elide: Text.ElideRight
            }
            QQC2.Label {
                Layout.fillWidth: true
                text: item.summary
                wrapMode: Text.WordWrap
                maximumLineCount: 2
                elide: Text.ElideRight
                visible: text !== ""
            }
            QQC2.Label {
                Layout.fillWidth: true
                text: item.source
                opacity: 0.7
                font: Kirigami.Theme.smallFont
                elide: Text.ElideRight
            }
            QQC2.Label {
                Layout.fillWidth: true
                text: item.status
                visible: text !== ""
                wrapMode: Text.WordWrap
            }
            QQC2.ProgressBar {
                Layout.fillWidth: true
                visible: item.busy
                indeterminate: item.progress < 0
                from: 0
                to: 100
                value: Math.max(0, item.progress)
            }
            Kirigami.InlineMessage {
                Layout.fillWidth: true
                visible: item.problem !== ""
                type: Kirigami.MessageType.Error
                text: item.problem
                actions: [
                    Kirigami.Action {
                        text: item.s["common.details"]
                        visible: item.details !== ""
                        onTriggered: detailsDialog.open()
                    }
                ]
            }
        }

        ColumnLayout {
            Layout.alignment: Qt.AlignTop
            spacing: Kirigami.Units.smallSpacing

            QQC2.Button {
                Layout.alignment: Qt.AlignRight
                text: item.installed ? item.s["apps.remove"] : item.s["apps.install"]
                icon.name: item.installed ? "edit-delete" : "download"
                enabled: !item.busy
                onClicked: item.installed ? removeDialog.open() : item.appsModel.install(item.index)
            }
            QQC2.ToolButton {
                id: othersButton
                Layout.alignment: Qt.AlignRight
                text: item.s["apps.other_versions"]
                visible: item.others.length > 0
                enabled: !item.busy
                onClicked: othersMenu.popup(othersButton, 0, othersButton.height)

                QQC2.Menu {
                    id: othersMenu
                    Repeater {
                        model: item.others
                        QQC2.MenuItem {
                            required property int index
                            required property string modelData
                            text: modelData
                            onTriggered: item.appsModel.installFrom(item.index, index)
                        }
                    }
                }
            }
        }
    }

    Kirigami.PromptDialog {
        id: removeDialog
        title: item.s["apps.remove"]
        subtitle: item.s["apps.confirm_remove"].replace("{name}", item.name)
        standardButtons: Kirigami.Dialog.Ok | Kirigami.Dialog.Cancel
        onAccepted: item.appsModel.remove(item.index)
    }

    Kirigami.PromptDialog {
        id: detailsDialog
        title: item.s["common.details"]
        subtitle: item.details
        standardButtons: Kirigami.Dialog.Close
    }
}
