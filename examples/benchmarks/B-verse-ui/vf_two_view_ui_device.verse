using { /Fortnite.com/Devices }
using { /Fortnite.com/UI }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/UI }
using { /UnrealEngine.com/Temporary/SpatialMath }

# VerseForge benchmark B. Original source; UEFN compile NOT TESTED.
# A creative Button toggles a per-player, two-view interactive Verse canvas.
vf_two_view_ui_device := class(creative_device):
    @editable
    OpenButton:button_device = button_device{}

    var ActiveUI:[player]?canvas = map{}
    var ActiveView:[player]int = map{}
    var UIListeners:[player][]cancelable = map{}
    var OpenSubscription:?cancelable = false
    var LeaveSubscription:?cancelable = false

    TitleOne<localizes>:message = "VerseForge / Home"
    TitleTwo<localizes>:message = "VerseForge / Details"
    NavigateLabel<localizes>:message = "Switch view"
    CloseLabel<localizes>:message = "Close"

    OnBegin<override>()<suspends>:void =
        set OpenSubscription = option{OpenButton.InteractedWithEvent.Subscribe(OnOpen)}
        set LeaveSubscription = option{GetPlayspace().PlayerRemovedEvent().Subscribe(OnPlayerLeft)}

    OnOpen(Who:agent):void =
        if (P := player[Who]):
            if (Existing := ActiveUI[P]?):
                CloseForPlayer(P)
            else:
                OpenForPlayer(P, 0)

    OpenForPlayer(P:player, View:int):void =
        CloseForPlayer(P)
        if (PUI := GetPlayerUI[P]):
            var Heading:message = TitleOne
            if (View = 1):
                set Heading = TitleTwo
            TitleWidget:text_block = text_block{DefaultText := Heading}
            NextButton:button_loud = button_loud{DefaultText := NavigateLabel}
            ExitButton:button_regular = button_regular{DefaultText := CloseLabel}
            NextListener := NextButton.OnClick().Subscribe(OnNavigate)
            ExitListener := ExitButton.OnClick().Subscribe(OnExit)
            NewCanvas:canvas = canvas:
                Slots := array:
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.35}, Maximum := vector2{X := 0.5, Y := 0.35}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                        Widget := TitleWidget
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.50}, Maximum := vector2{X := 0.5, Y := 0.50}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                        Widget := NextButton
                    canvas_slot:
                        Anchors := anchors{Minimum := vector2{X := 0.5, Y := 0.62}, Maximum := vector2{X := 0.5, Y := 0.62}}
                        Alignment := vector2{X := 0.5, Y := 0.5}
                        SizeToContent := true
                        Widget := ExitButton
            PUI.AddWidget(NewCanvas, player_ui_slot{InputMode := ui_input_mode.All})
            if (set ActiveUI[P] = option{NewCanvas}) {}
            if (set ActiveView[P] = View) {}
            if (set UIListeners[P] = array{NextListener, ExitListener}) {}

    OnNavigate(Event:widget_message):void =
        if (View := ActiveView[Event.Player]):
            if (View = 0):
                OpenForPlayer(Event.Player, 1)
            else:
                OpenForPlayer(Event.Player, 0)

    OnExit(Event:widget_message):void =
        CloseForPlayer(Event.Player)

    CloseForPlayer(P:player):void =
        if (Listeners := UIListeners[P]):
            for (Listener : Listeners):
                Listener.Cancel()
        if (PUI := GetPlayerUI[P], Widget := ActiveUI[P]?):
            PUI.RemoveWidget(Widget)
        if (set ActiveUI[P] = false) {}
        if (set UIListeners[P] = array{}) {}

    OnPlayerLeft(P:player):void =
        CloseForPlayer(P)

    OnEnd<override>():void =
        if (Subscription := OpenSubscription?):
            Subscription.Cancel()
        if (Subscription := LeaveSubscription?):
            Subscription.Cancel()
        for (P -> MaybeWidget : ActiveUI):
            CloseForPlayer(P)
