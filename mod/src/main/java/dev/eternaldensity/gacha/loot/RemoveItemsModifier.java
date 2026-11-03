package dev.eternaldensity.gacha.loot;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.neoforged.neoforge.common.loot.IGlobalLootModifier;
import net.neoforged.neoforge.common.loot.LootModifier;

import net.minecraft.core.registries.BuiltInRegistries;

import dev.eternaldensity.gacha.GachaMod;

import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import java.util.List;

/**
 * Global loot modifier: strips configured item stacks from configured loot
 * tables. The stripped items are registered as Item entries by the pack author
 * (conservation of loot, PROJECT_PLAN.md section 6.12); the modifier only
 * performs the strip.
 */
public class RemoveItemsModifier extends LootModifier {

    public static final MapCodec<RemoveItemsModifier> CODEC = RecordCodecBuilder.mapCodec(instance -> instance.group(
            IGlobalLootModifier.LOOT_CONDITIONS_CODEC.fieldOf("conditions").forGetter(m -> m.conditions),
            ResourceLocation.CODEC.listOf().fieldOf("tables").forGetter(m -> m.tables),
            Codec.DOUBLE.optionalFieldOf("chance", 1.0).forGetter(m -> m.chance),
            Codec.STRING.listOf().optionalFieldOf("items", List.of()).forGetter(m -> m.items),
            Codec.STRING.listOf().optionalFieldOf("tags", List.of()).forGetter(m -> m.tags),
            Codec.INT.optionalFieldOf("max_stacks", 1).forGetter(m -> m.maxStacks)
    ).apply(instance, RemoveItemsModifier::new));

    private final List<ResourceLocation> tables;
    private final double chance;
    private final List<String> items;
    private final List<String> tags;
    private final int maxStacks;

    public RemoveItemsModifier(LootItemCondition[] conditions, List<ResourceLocation> tables,
                               double chance, List<String> items, List<String> tags, int maxStacks) {
        super(conditions);
        this.tables = tables;
        this.chance = chance;
        this.items = items;
        this.tags = tags;
        this.maxStacks = maxStacks;
    }

    @Override
    protected ObjectArrayList<ItemStack> doApply(ObjectArrayList<ItemStack> generatedLoot, LootContext context) {
        ResourceLocation tableId = context.getQueriedLootTableId();
        if (tableId == null || !tables.contains(tableId)) {
            return generatedLoot;
        }
        if (context.getRandom().nextFloat() >= chance) {
            return generatedLoot;
        }
        List<ResourceLocation> itemIds = items.stream().map(ResourceLocation::parse).toList();
        List<TagKey<Item>> tagKeys = tags.stream().map(tag -> {
            String id = tag.startsWith("#") ? tag.substring(1) : tag;
            return TagKey.create(Registries.ITEM, ResourceLocation.parse(id));
        }).toList();

        int removed = 0;
        var iterator = generatedLoot.iterator();
        while (iterator.hasNext() && removed < maxStacks) {
            ItemStack stack = iterator.next();
            boolean matches = false;
            for (ResourceLocation itemId : itemIds) {
                Item item = BuiltInRegistries.ITEM.getOptional(itemId).orElse(null);
                if (item != null && stack.getItem() == item) {
                    matches = true;
                    break;
                }
            }
            if (!matches) {
                for (TagKey<Item> tag : tagKeys) {
                    if (stack.is(tag)) {
                        matches = true;
                        break;
                    }
                }
            }
            if (matches) {
                iterator.remove();
                removed++;
            }
        }
        return generatedLoot;
    }

    @Override
    public MapCodec<? extends IGlobalLootModifier> codec() {
        return dev.eternaldensity.gacha.loot.GachaLootModifiers.REMOVE_ITEMS.get();
    }
}
