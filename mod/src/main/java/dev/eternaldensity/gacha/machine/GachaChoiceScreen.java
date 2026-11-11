package dev.eternaldensity.gacha.machine;

import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.ClickType;

import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

@OnlyIn(Dist.CLIENT)
public class GachaChoiceScreen extends AbstractContainerScreen<GachaChoiceMenu> {
    public GachaChoiceScreen(GachaChoiceMenu menu, Inventory inv, Component title) {
        super(menu, inv, title);
        this.imageWidth = 176;
        this.imageHeight = 166;
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTick, int mouseX, int mouseY) {
        // Simple background.
        graphics.fill(this.leftPos, this.topPos, this.leftPos + this.imageWidth, this.topPos + this.imageHeight, 0xCC000000);
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(this.font, this.title, 8, 6, 0xFFFFFF);
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float partialTick) {
        super.render(graphics, mouseX, mouseY, partialTick);
        // Draw result/category labels.
        int y = this.topPos + 18;
        if (menu.getStage() == GachaChoiceMenu.Stage.ADVANTAGE) {
            for (int i = 0; i < menu.getResults().size(); i++) {
                var r = menu.getResults().get(i);
                graphics.drawString(this.font, (i + 1) + ". " + r.tier() + " " + r.name(), this.leftPos + 18, y + i * 12, 0xFFFFFF);
            }
        } else {
            for (int i = 0; i < menu.getCategories().size(); i++) {
                graphics.drawString(this.font, (i + 1) + ". " + menu.getCategories().get(i), this.leftPos + 18, y + i * 12, 0xFFFFFF);
            }
        }
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        // Clicking anywhere in a result row grants it; map by row.
        int relY = (int) (mouseY - (this.topPos + 18));
        int idx = relY / 12;
        int count = (menu.getStage() == GachaChoiceMenu.Stage.ADVANTAGE)
                ? menu.getResults().size() : menu.getCategories().size();
        if (idx >= 0 && idx < count) {
            this.menu.clicked(idx, button, ClickType.PICKUP, this.minecraft.player);
            return true;
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }
}
