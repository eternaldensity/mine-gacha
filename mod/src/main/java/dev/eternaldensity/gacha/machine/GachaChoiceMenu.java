package dev.eternaldensity.gacha.machine;

import dev.eternaldensity.gacha.GachaMod;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

import java.util.ArrayList;
import java.util.List;

/**
 * Container menu backing the result chooser GUI. The server constructs it
 * with the pending results; the client reconstructs it from the buffer.
 * Clicking a result slot grants that result; clicking a category slot picks
 * the category for a choice ticket.
 */
public class GachaChoiceMenu extends AbstractContainerMenu {
    public enum Stage { CATEGORY, ADVANTAGE }

    public static final int RESULT_SLOTS = 6;

    private Stage stage;
    private final List<ChoiceService.ResultView> results = new ArrayList<>();
    private final List<String> categories = new ArrayList<>();
    private final int resultCount;

    // Server-side constructor (results already rolled).
    public GachaChoiceMenu(int containerId, Inventory inv, Stage stage, List<ChoiceService.ResultView> results, List<String> categories) {
        super(GachaMenus.CHOICE.get(), containerId);
        this.stage = stage;
        if (results != null) this.results.addAll(results);
        if (categories != null) this.categories.addAll(categories);
        this.resultCount = this.results.size();
        buildSlots(inv);
    }

    // Client-side constructor.
    public GachaChoiceMenu(int containerId, Inventory inv, RegistryFriendlyByteBuf buf) {
        super(GachaMenus.CHOICE.get(), containerId);
        int stageOrdinal = buf.readVarInt();
        this.stage = Stage.values()[Math.max(0, Math.min(Stage.values().length - 1, stageOrdinal))];
        int n = buf.readVarInt();
        for (int i = 0; i < n; i++) {
            this.results.add(new ChoiceService.ResultView(buf.readUtf(), buf.readUtf(), buf.readDouble()));
        }
        int m = buf.readVarInt();
        for (int i = 0; i < m; i++) {
            this.categories.add(buf.readUtf());
        }
        this.resultCount = this.results.size();
        buildSlots(inv);
    }

    private void buildSlots(Inventory inv) {
        // Result/category slots at top.
        int slotIndex = 0;
        if (stage == Stage.ADVANTAGE) {
            for (int i = 0; i < Math.min(results.size(), RESULT_SLOTS); i++) {
                addSlot(new Slot(new net.minecraft.world.SimpleContainer(RESULT_SLOTS), i, 18 + i * 18, 18) {
                    @Override
                    public boolean mayPlace(ItemStack stack) { return false; }
                });
            }
        } else {
            for (int i = 0; i < Math.min(categories.size(), RESULT_SLOTS); i++) {
                addSlot(new Slot(new net.minecraft.world.SimpleContainer(RESULT_SLOTS), i, 18 + i * 18, 18) {
                    @Override
                    public boolean mayPlace(ItemStack stack) { return false; }
                });
            }
        }
        // Player inventory (3 rows).
        for (int row = 0; row < 3; row++) {
            for (int col = 0; col < 9; col++) {
                addSlot(new Slot(inv, col + row * 9 + 9, 8 + col * 18, 84 + row * 18));
            }
        }
        // Hotbar.
        for (int col = 0; col < 9; col++) {
            addSlot(new Slot(inv, col, 8 + col * 18, 142));
        }
    }

    public Stage getStage() { return stage; }
    public List<ChoiceService.ResultView> getResults() { return results; }
    public List<String> getCategories() { return categories; }

    @Override
    public boolean stillValid(Player player) { return true; }

    @Override
    public void clicked(int slotId, int button, ClickType clickType, Player player) {
        if (slotId >= 0 && slotId < (stage == Stage.ADVANTAGE ? results.size() : categories.size())) {
            // Handle on server side only.
            if (player instanceof net.minecraft.server.level.ServerPlayer sp) {
                if (stage == Stage.ADVANTAGE) {
                    ChoiceService.chooseResult(sp, slotId + 1);
                } else {
                    ChoiceService.chooseCategory(sp, categories.get(slotId));
                }
                // Close the menu after a choice.
                sp.closeContainer();
            }
            return;
        }
        super.clicked(slotId, button, clickType, player);
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) { return ItemStack.EMPTY; }

    public static void writeBuf(RegistryFriendlyByteBuf buf, Stage stage, List<ChoiceService.ResultView> results, List<String> categories) {
        buf.writeVarInt(stage.ordinal());
        buf.writeVarInt(results.size());
        for (ChoiceService.ResultView r : results) {
            buf.writeUtf(r.name());
            buf.writeUtf(r.tier());
            buf.writeDouble(r.rarity());
        }
        buf.writeVarInt(categories.size());
        for (String c : categories) buf.writeUtf(c);
    }
}
