package dev.eternaldensity.gacha.entry;

import com.mojang.serialization.Dynamic;
import net.minecraft.core.Holder;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;

/**
 * Applies an entry's reward. Implemented adapters: {@code gacha:item},
 * {@code gacha:attribute} and {@code gacha:effect}. {@code gacha:mob} and
 * {@code gacha:command} are declared in the schema but not yet applied; entries
 * using them are excluded from the pool rather than failing after a roll.
 */
public final class EntryAdapters {
    private EntryAdapters() {
    }

    public static boolean apply(Player player, ResourceLocation entryId, Entry entry) {
        Dynamic<?> adapter = entry.adapter().orElse(null);
        if (adapter == null) {
            return false;
        }
        return switch (adapter.get("type").asString("")) {
            case "gacha:item" -> applyItem(player, adapter);
            case "gacha:attribute" -> applyAttribute(player, entryId, adapter);
            case "gacha:effect" -> applyEffect(player, adapter);
            case "gacha:origin" -> OriginAdapter.apply(player, adapter);
            default -> false;
        };
    }

    private static boolean applyItem(Player player, Dynamic<?> adapter) {
        ResourceLocation itemId = ResourceLocation.tryParse(adapter.get("item").asString(""));
        if (itemId == null) {
            return false;
        }
        Item item = BuiltInRegistries.ITEM.getOptional(itemId).orElse(null);
        if (item == null || item == Items.AIR) {
            return false;
        }
        int count = Math.max(1, adapter.get("count").asInt(1));
        ItemStack stack = new ItemStack(item, count);
        if (!player.addItem(stack)) {
            player.drop(stack, false);
        }
        return true;
    }

    private static boolean applyAttribute(Player player, ResourceLocation entryId, Dynamic<?> adapter) {
        ResourceLocation attributeId = ResourceLocation.tryParse(adapter.get("attribute").asString(""));
        if (attributeId == null) {
            return false;
        }
        Holder<Attribute> attribute = BuiltInRegistries.ATTRIBUTE.getHolder(attributeId).orElse(null);
        if (attribute == null) {
            return false;
        }
        AttributeInstance instance = player.getAttribute(attribute);
        if (instance == null) {
            return false;
        }
        AttributeModifier.Operation operation = switch (adapter.get("operation").asString("add")) {
            case "multiply_base" -> AttributeModifier.Operation.ADD_MULTIPLIED_BASE;
            case "multiply_total" -> AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL;
            default -> AttributeModifier.Operation.ADD_VALUE;
        };
        double amount = adapter.get("amount").asDouble(0.0);
        ResourceLocation modifierId = entryId.withPrefix("entry/");
        instance.addTransientModifier(new AttributeModifier(modifierId, amount, operation));
        return true;
    }

    private static boolean applyEffect(Player player, Dynamic<?> adapter) {
        ResourceLocation effectId = ResourceLocation.tryParse(adapter.get("effect").asString(""));
        if (effectId == null) {
            return false;
        }
        Holder<MobEffect> effect = BuiltInRegistries.MOB_EFFECT.getHolder(effectId).orElse(null);
        if (effect == null) {
            return false;
        }
        int duration = adapter.get("duration").asInt(-1);
        if (duration < 0) {
            duration = MobEffectInstance.INFINITE_DURATION;
        }
        int amplifier = Math.max(0, adapter.get("amplifier").asInt(0));
        player.addEffect(new MobEffectInstance(effect, duration, amplifier));
        return true;
    }
}
