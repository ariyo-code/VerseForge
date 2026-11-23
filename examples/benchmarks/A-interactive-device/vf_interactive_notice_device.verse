using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }

# VerseForge benchmark A. Original source; UEFN compile NOT TESTED.
# Place this device, a Button and a HUD Message in the editor and assign both @editables.
vf_interactive_notice_device := class(creative_device):
    @editable
    Trigger:button_device = button_device{}

    @editable
    Notice:hud_message_device = hud_message_device{}

    var TriggerSubscription:?cancelable = false

    ActivatedText<localizes>(Who:agent):message = "Interaction received from {Who}."

    OnBegin<override>()<suspends>:void =
        set TriggerSubscription = option{Trigger.InteractedWithEvent.Subscribe(OnInteracted)}

    OnInteracted(Who:agent):void =
        # Targeted, per-agent message; no global notification or polling.
        Notice.Show(Who, ActivatedText(Who), 3.0)

    OnEnd<override>():void =
        if (Subscription := TriggerSubscription?):
            Subscription.Cancel()
        set TriggerSubscription = false
