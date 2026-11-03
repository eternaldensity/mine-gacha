package dev.eternaldensity.gacha.loot;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootContext;
import net.minecraft.world.level.storage.loot.predicates.LootItemCondition;
import net.neoforged.neoforge.common.loot.IGlobalLootModifier;
import net.neoforged.neoforge.common.loot.LootModifier;

import dev.eternaldensity.gacha.GachaComponents;
import dev.eternaldensity.gacha.GachaItems;
import dev.eternaldensity.gacha.ticket.TicketData;

import it.unimi.dsi.fastutil.objects.ObjectArrayList;
import java.util.List;

/**
 * Global loot modifier: injects gacha tickets into configured loot tables.
 *
 * <p>Config shape: {@code {"type":"gacha:add_ticket","tables":[...],
 * "chance":1.0,"ticket":{...},"count":{"min":1,"max":1}}}.
 */
public class AddTicketModifier extends LootModifier {

    public record CountRange(int min, int max) {
        public static final Codec<CountRange> CODEC = RecordCodecBuilder.create(instance -> instance.group(
                Codec.INT.fieldOf("min").forGetter(CountRange::min),
                Codec.INT.fieldOf("max").forGetter(CountRange::max)
        ).apply(instance, CountRange::new));
    }

    public static final MapCodec<AddTicketModifier> CODEC = RecordCodecBuilder.mapCodec(instance -> instance.group(
            IGlobalLootModifier.LOOT_CONDITIONS_CODEC.fieldOf("conditions").forGetter(m -> m.conditions),
            ResourceLocation.CODEC.listOf().fieldOf("tables").forGetter(m -> m.tables),
            Codec.DOUBLE.optionalFieldOf("chance", 1.0).forGetter(m -> m.chance),
            TicketData.CODEC.fieldOf("ticket").forGetter(m -> m.ticket),
            CountRange.CODEC.optionalFieldOf("count", new CountRange(1, 1)).forGetter(m -> m.count)
    ).apply(instance, AddTicketModifier::new));

    private final List<ResourceLocation> tables;
    private final double chance;
    private final TicketData ticket;
    private final CountRange count;

    public AddTicketModifier(LootItemCondition[] conditions, List<ResourceLocation> tables,
                             double chance, TicketData ticket, CountRange count) {
        super(conditions);
        this.tables = tables;
        this.chance = chance;
        this.ticket = ticket;
        this.count = count;
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
        int amount = count.min() + (count.max() > count.min()
                ? context.getRandom().nextInt(count.max() - count.min() + 1) : 0);
        for (int i = 0; i < amount; i++) {
            ItemStack stack = new ItemStack(GachaItems.TICKET.get());
            stack.set(GachaComponents.TICKET.get(), ticket);
            generatedLoot.add(stack);
        }
        return generatedLoot;
    }

    @Override
    public MapCodec<? extends IGlobalLootModifier> codec() {
        return dev.eternaldensity.gacha.loot.GachaLootModifiers.ADD_TICKET.get();
    }
}
