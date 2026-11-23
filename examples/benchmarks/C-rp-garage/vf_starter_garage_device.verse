using { /Fortnite.com/Devices }
using { /Verse.org/Simulation }

# VerseForge benchmark C: starter garage with PERSISTENT entitlement, actual
# vehicle respawn/destroy, a HUD notification and real interactive popup.
# This is NOT a paid economy; integration with an existing wallet is necessary
# before adding purchases, and lock/vehicle-theft enforcement is NOT provided.
# UEFN compile: NOT TESTED. Runtime: NOT TESTED. Multiplayer: NOT TESTED.
vf_starter_garage_device := class(creative_device):
    @editable
    GarageEntrance:button_device = button_device{}

    @editable
    GarageMenu:popup_dialog_device = popup_dialog_device{}

    @editable
    Feedback:hud_message_device = hud_message_device{}

    # Configure a Whiplash spawner per simultaneously served player.
    @editable
    CarSpawners:[]vehicle_spawner_sports_car_device = array{}

    var SlotOwners:[]?player = array{}
    var EntranceSubscription:?cancelable = false
    var MenuSubscription:?cancelable = false
    var LeftSubscription:?cancelable = false
    var JoinedSubscription:?cancelable = false

    Received<localizes>:message = "Starter car acquired and saved."
    AlreadyOwned<localizes>:message = "You already own your starter car."
    NotOwned<localizes>:message = "Claim your starter car first."
    Full<localizes>:message = "All garage bays are currently occupied."
    Retrieved<localizes>:message = "Your car is ready at its reserved bay."
    Stored<localizes>:message = "Your car is stored."
    NoActive<localizes>:message = "No active car to store."
    FailedSave<localizes>:message = "Could not save your ownership. Try again."

    OnBegin<override>()<suspends>:void =
        for (Car : CarSpawners):
            set SlotOwners += array{false}
        for (P : GetPlayspace().GetPlayers()):
            InitializeProfile(P)
        set EntranceSubscription = option{GarageEntrance.InteractedWithEvent.Subscribe(ShowGarage)}
        set MenuSubscription = option{GarageMenu.RespondingButtonEvent.Subscribe(OnGarageCommand)}
        set JoinedSubscription = option{GetPlayspace().PlayerAddedEvent().Subscribe(InitializeProfile)}
        set LeftSubscription = option{GetPlayspace().PlayerRemovedEvent().Subscribe(OnPlayerLeft)}

    InitializeProfile(P:player):void =
        if:
            not VFStarterGarageProfiles[P]
            set VFStarterGarageProfiles[P] = vf_garage_profile{}

    ShowGarage(Who:agent):void =
        # Configure popup buttons in UEFN: index 0 = Claim, 1 = Retrieve, 2 = Store.
        GarageMenu.Show(Who)

    OnGarageCommand(Command:tuple(agent,int)):void =
        Who := Command(0)
        Choice := Command(1)
        if (P := player[Who]):
            if (Choice = 0):
                ClaimStarter(P)
            else if (Choice = 1):
                Retrieve(P)
            else if (Choice = 2):
                Store(P)

    ClaimStarter(P:player):void =
        if (Old := VFStarterGarageProfiles[P]):
            if (Old.HasStarterCar?):
                Feedback.Show(P, AlreadyOwned, 2.0)
            else:
                if (set VFStarterGarageProfiles[P] = vf_garage_profile{Version := Old.Version, HasStarterCar := true}):
                    Feedback.Show(P, Received, 2.0)
                else:
                    Feedback.Show(P, FailedSave, 2.0)

    OwnedSlot(P:player):?int =
        for (Index -> MaybeOwner : SlotOwners):
            if (Owner := MaybeOwner?, Owner = P):
                return option{Index}
        return false

    FreeSlot():?int =
        for (Index -> MaybeOwner : SlotOwners):
            if (not MaybeOwner?):
                return option{Index}
        return false

    Retrieve(P:player):void =
        if (Profile := VFStarterGarageProfiles[P], Profile.HasStarterCar?):
            if (Current := OwnedSlot(P)?):
                # Existing car is already out. Do not respawn/destroy it.
                Feedback.Show(P, Retrieved, 2.0)
            else:
                if (Slot := FreeSlot()?, Spawner := CarSpawners[Slot]):
                    # No suspending operations between reservation and assignment.
                    if (set SlotOwners[Slot] = option{P}):
                        Spawner.RespawnVehicle()
                        Feedback.Show(P, Retrieved, 2.0)
                else:
                    Feedback.Show(P, Full, 2.0)
        else:
            Feedback.Show(P, NotOwned, 2.0)

    Store(P:player):void =
        if (Slot := OwnedSlot(P)?, Spawner := CarSpawners[Slot]):
            Spawner.DestroyVehicle()
            if (set SlotOwners[Slot] = false) {}
            Feedback.Show(P, Stored, 2.0)
        else:
            Feedback.Show(P, NoActive, 2.0)

    OnPlayerLeft(P:player):void =
        # Keep the persistent profile; only free the ephemeral physical bay.
        if (Slot := OwnedSlot(P)?, Spawner := CarSpawners[Slot]):
            Spawner.DestroyVehicle()
            if (set SlotOwners[Slot] = false) {}

    OnEnd<override>():void =
        if (S := EntranceSubscription?):
            S.Cancel()
        if (S := MenuSubscription?):
            S.Cancel()
        if (S := JoinedSubscription?):
            S.Cancel()
        if (S := LeftSubscription?):
            S.Cancel()
