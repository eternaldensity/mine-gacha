package dev.eternaldensity.gacha.test;

import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaBlocks;
import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.GachaMod;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.entry.EntryPool;
import dev.eternaldensity.gacha.machine.MachineService;
import dev.eternaldensity.gacha.ticket.RollSpec;
import dev.eternaldensity.gacha.ticket.TicketData;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.gametest.framework.GameTest;
import net.minecraft.gametest.framework.GameTestHelper;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.gametest.GameTestHolder;

import java.util.Optional;

/**
 * Player-in-the-loop end-to-end checks: ticket → roll → reward → Power Score →
 * advancement. Run with {@code ./gradlew runGameTestServer}.
 */
@GameTestHolder(GachaMod.MOD_ID)
public class GachaGameTest {

    /** A ticket that can only resolve to the top starter item (diamond pickaxe, rarity 4.4). */
    private static ItemStack narrowItemTicket() {
        return narrowTicket("item", 4.3, 4.4, 4.5);
    }

    /**
     * A ticket that can only resolve to the starter trait (feather charm, rarity
     * 2.4): its duplicate policy is insight, so a second copy becomes residue
     * rather than stacking.
     */
    private static ItemStack narrowTraitTicket() {
        return narrowTicket("trait", 2.3, 2.4, 2.5);
    }

    private static ItemStack narrowTicket(String category, double min, double avg, double max) {
        ItemStack stack = new ItemStack(GachaItems.TICKET.get());
        TicketData data = new TicketData(
                1,
                category,
                new RollSpec(min, avg, max, false),
                1,
                Optional.empty(),
                Optional.empty(),
                Optional.of("bronze"));
        stack.set(GachaComponents.TICKET.get(), data);
        return stack;
    }

    @GameTest(template = "empty", templateNamespace = "gacha", timeoutTicks = 200)
    public static void ticketToReward(GameTestHelper helper) {
        ServerPlayer player = helper.makeMockServerPlayerInLevel();
        ItemStack ticket = narrowItemTicket();
        player.setItemInHand(InteractionHand.MAIN_HAND, ticket);

        var registry = helper.getLevel().registryAccess().registryOrThrow(GachaRegistries.ENTRY);
        helper.assertTrue(registry.size() > 0, "the entry registry should load, got " + registry.size());
        var pool = EntryPool.candidates(registry, "item", Optional.empty());
        helper.assertTrue(!pool.isEmpty(), "the item pool should not be empty");

        boolean opened = MachineService.open(helper.getLevel(), player, ticket);
        helper.assertTrue(opened, "the ticket should resolve");
        helper.assertTrue(ticket.isEmpty(), "the ticket should be consumed");

        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        helper.assertTrue(state.ownedEntries().size() == 1,
                "exactly one entry should be owned, got " + state.ownedEntries());
        helper.assertTrue(state.powerScore() > 0.0, "the Power Score should be positive");
        helper.assertTrue(player.getInventory().countItem(Items.DIAMOND_PICKAXE) > 0,
                "the diamond pickaxe reward should be in the inventory");

        var advancement = helper.getLevel().getServer().getAdvancements()
                .get(ResourceLocation.fromNamespaceAndPath("gacha", "first_roll"));
        helper.assertTrue(advancement != null, "the first_roll advancement should exist");
        helper.assertTrue(player.getAdvancements().getOrStartProgress(advancement).isDone(),
                "the first_roll advancement should be granted");
        helper.succeed();
    }

    @GameTest(template = "empty", templateNamespace = "gacha", timeoutTicks = 200)
    public static void chestInjectsTicket(GameTestHelper helper) {
        var key = ResourceKey.create(
                Registries.LOOT_TABLE,
                ResourceLocation.fromNamespaceAndPath("minecraft", "chests/village/village_plains_house"));
        var table = helper.getLevel().getServer().reloadableRegistries().getLootTable(key);
        var params = new LootParams.Builder(helper.getLevel())
                .withParameter(LootContextParams.ORIGIN, Vec3.atCenterOf(helper.absolutePos(new BlockPos(1, 1, 1))))
                .create(LootContextParamSets.CHEST);

        boolean found = false;
        int size = 0;
        for (int attempt = 0; attempt < 8 && !found; attempt++) {
            var loot = table.getRandomItems(params);
            size = loot.size();
            found = loot.stream().anyMatch(stack -> stack.is(GachaItems.TICKET.get()));
        }
        helper.assertTrue(found,
                "a listed village chest should inject a ticket (id=" + table.getLootTableId()
                        + ", last size=" + size + ")");
        helper.succeed();
    }

    @GameTest(template = "empty", templateNamespace = "gacha", timeoutTicks = 200)
    public static void machineBlockRollsTicket(GameTestHelper helper) {
        ServerPlayer player = helper.makeMockServerPlayerInLevel();
        BlockPos pos = new BlockPos(1, 1, 1);
        helper.setBlock(pos, GachaBlocks.MACHINE.get());

        ItemStack ticket = narrowItemTicket();
        player.setItemInHand(InteractionHand.MAIN_HAND, ticket);

        // The full player path: right-click the machine with a ticket in hand.
        helper.useBlock(pos, player);

        helper.assertTrue(ticket.isEmpty(), "the machine should consume the ticket");
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        helper.assertTrue(state.ownedEntries().size() == 1,
                "the machine should record the reward, got " + state.ownedEntries());
        helper.assertTrue(state.powerScore() > 0.0, "the machine should recompute the Power Score");
        helper.assertTrue(player.getInventory().countItem(Items.DIAMOND_PICKAXE) > 0,
                "the machine should grant the reward item");
        helper.succeed();
    }

    @GameTest(template = "empty", templateNamespace = "gacha", timeoutTicks = 200)
    public static void duplicateGrantsResidue(GameTestHelper helper) {
        ServerPlayer player = helper.makeMockServerPlayerInLevel();

        ItemStack first = narrowTraitTicket();
        player.setItemInHand(InteractionHand.MAIN_HAND, first);
        helper.assertTrue(MachineService.open(helper.getLevel(), player, first), "the first ticket should resolve");

        ItemStack second = narrowTraitTicket();
        player.setItemInHand(InteractionHand.MAIN_HAND, second);
        helper.assertTrue(MachineService.open(helper.getLevel(), player, second), "the duplicate should resolve");

        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        helper.assertTrue(state.ownedEntries().size() == 1, "the duplicate must not add a second owned entry");
        helper.assertTrue(state.residue().getOrDefault("Bronze", 0) == 1,
                "the duplicate should grant 1 Bronze Residue, got " + state.residue());

        var advancement = helper.getLevel().getServer().getAdvancements()
                .get(ResourceLocation.fromNamespaceAndPath("gacha", "first_duplicate"));
        helper.assertTrue(advancement != null, "the first_duplicate advancement should exist");
        helper.assertTrue(player.getAdvancements().getOrStartProgress(advancement).isDone(),
                "the first_duplicate advancement should be granted");
        helper.succeed();
    }
}
