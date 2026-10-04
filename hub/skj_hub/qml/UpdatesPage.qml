// Updates: one button for everything. A restart is offered, never forced.
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page

    readonly property var s: hub.strings
    readonly property var ctl: hub.updates

    title: s["nav.updates"]

    actions: [
        Kirigami.Action {
            text: page.s["start.check_updates"]
            icon.name: "view-refresh"
            enabled: page.ctl.state !== "checking" && page.ctl.state !== "running"
            onTriggered: page.ctl.check()
        }
    ]

    ColumnLayout {
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: page.ctl.problem !== ""
            type: Kirigami.MessageType.Error
            text: page.ctl.problem
        }

        Kirigami.InlineMessage {
            Layout.fillWidth: true
            visible: page.ctl.restartState !== "none"
            type: page.ctl.restartState === "wait" ? Kirigami.MessageType.Information
                                                   : Kirigami.MessageType.Warning
            text: page.ctl.restartState === "wait" ? page.s["updates.wait_driver"]
                                                   : page.s["updates.restart_needed"]
            actions: [
                Kirigami.Action {
                    text: page.s["updates.restart_now"]
                    icon.name: "system-reboot"
                    enabled: page.ctl.restartState === "ready"
                    onTriggered: page.ctl.restartNow()
                },
                Kirigami.Action {
                    text: page.s["updates.later"]
                    onTriggered: page.ctl.later()
                }
            ]
        }

        Kirigami.Icon {
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: Kirigami.Units.gridUnit
            Layout.preferredWidth: Kirigami.Units.iconSizes.enormous
            Layout.preferredHeight: Kirigami.Units.iconSizes.enormous
            source: page.ctl.state === "ready" ? "update-low"
                  : page.ctl.state === "running" || page.ctl.state === "checking" ? "view-refresh"
                  : "checkmark"
        }

        Kirigami.Heading {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: page.ctl.summary
            level: 2
            wrapMode: Text.WordWrap
        }

        QQC2.Label {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: page.s["updates.why"]
            wrapMode: Text.WordWrap
            opacity: 0.7
        }

        QQC2.Button {
            Layout.alignment: Qt.AlignHCenter
            visible: page.ctl.state === "ready"
            text: page.s["updates.button"]
            icon.name: "system-software-update"
            highlighted: true
            onClicked: page.ctl.apply()
        }

        QQC2.ProgressBar {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
            Layout.alignment: Qt.AlignHCenter
            visible: page.ctl.state === "running" || page.ctl.state === "checking"
            indeterminate: page.ctl.progress < 0 || page.ctl.state === "checking"
            from: 0
            to: 100
            value: Math.max(0, page.ctl.progress)
        }

        QQC2.CheckBox {
            id: showDetails
            Layout.alignment: Qt.AlignHCenter
            visible: page.ctl.details !== ""
            text: page.s["updates.details"]
        }

        QQC2.Label {
            Layout.fillWidth: true
            Layout.maximumWidth: Kirigami.Units.gridUnit * 30
            Layout.alignment: Qt.AlignHCenter
            visible: showDetails.checked && page.ctl.details !== ""
            text: page.ctl.details
            wrapMode: Text.WordWrap
        }
    }

    Component.onCompleted: {
        if (ctl.state === "checking" || ctl.state === "none") {
            ctl.check()
        }
    }
}
