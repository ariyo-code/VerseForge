using { /Verse.org/Simulation }

# A single persistable owner record for this standalone example. UEFN compile NOT TESTED.
# IMPORTANT: Never add a new weak_map to a published island without checking
# all existing persistent variables and compatibility/migration constraints.
vf_garage_profile := class<final><persistable>:
    Version:int = 1
    HasStarterCar:logic = false

# One weak_map for this example. Real RP projects should extend their existing
# canonical player profile rather than create a parallel owner of ownership.
var VFStarterGarageProfiles:weak_map(player, vf_garage_profile) = map{}
