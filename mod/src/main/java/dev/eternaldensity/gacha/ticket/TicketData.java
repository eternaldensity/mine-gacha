package dev.eternaldensity.gacha.ticket;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;

import java.util.List;
import java.util.Optional;

/**
 * The ticket's data component (PROJECT_PLAN.md section 6.3).
 *
 * <p>A ticket is a promise: it stores the numbers that were true when it was
 * granted (schema version, category, roll triple, Advantage, optional filter and
 * cosmetic origin), never a pointer to a preset that could be rebalanced later.
 */
public record TicketData(
        int schema,
        String category,
        RollSpec roll,
        int advantage,
        Optional<TicketFilter> filter,
        Optional<TicketOrigin> origin,
        Optional<String> depth) {

    public static final Codec<TicketData> CODEC = RecordCodecBuilder.create(instance -> instance.group(
            Codec.INT.optionalFieldOf("schema", 1).forGetter(TicketData::schema),
            Codec.STRING.fieldOf("category").forGetter(TicketData::category),
            RollSpec.CODEC.fieldOf("roll").forGetter(TicketData::roll),
            Codec.INT.optionalFieldOf("advantage", 1).forGetter(TicketData::advantage),
            TicketFilter.CODEC.optionalFieldOf("filter").forGetter(TicketData::filter),
            TicketOrigin.CODEC.optionalFieldOf("origin").forGetter(TicketData::origin),
            Codec.STRING.optionalFieldOf("depth").forGetter(TicketData::depth)
    ).apply(instance, TicketData::new));

    public static final StreamCodec<RegistryFriendlyByteBuf, TicketData> STREAM_CODEC =
            StreamCodec.of(TicketData::write, TicketData::read);

    private static void write(RegistryFriendlyByteBuf buffer, TicketData data) {
        buffer.writeVarInt(data.schema);
        buffer.writeUtf(data.category);
        buffer.writeDouble(data.roll.min());
        buffer.writeDouble(data.roll.avg());
        buffer.writeDouble(data.roll.max());
        buffer.writeBoolean(data.roll.flat());
        buffer.writeVarInt(data.advantage);
        buffer.writeBoolean(data.filter.isPresent());
        data.filter.ifPresent(filter -> {
            writeStrings(buffer, filter.tagsAll());
            writeStrings(buffer, filter.tagsAny());
        });
        buffer.writeBoolean(data.origin.isPresent());
        data.origin.ifPresent(origin -> {
            buffer.writeUtf(origin.type());
            buffer.writeUtf(origin.id());
        });
        buffer.writeBoolean(data.depth.isPresent());
        data.depth.ifPresent(buffer::writeUtf);
    }

    private static TicketData read(RegistryFriendlyByteBuf buffer) {
        int schema = buffer.readVarInt();
        String category = buffer.readUtf();
        RollSpec roll = new RollSpec(
                buffer.readDouble(), buffer.readDouble(), buffer.readDouble(), buffer.readBoolean());
        int advantage = buffer.readVarInt();
        Optional<TicketFilter> filter = buffer.readBoolean()
                ? Optional.of(new TicketFilter(readStrings(buffer), readStrings(buffer)))
                : Optional.empty();
        Optional<TicketOrigin> origin = buffer.readBoolean()
                ? Optional.of(new TicketOrigin(buffer.readUtf(), buffer.readUtf()))
                : Optional.empty();
        Optional<String> depth = buffer.readBoolean() ? Optional.of(buffer.readUtf()) : Optional.empty();
        return new TicketData(schema, category, roll, advantage, filter, origin, depth);
    }

    private static void writeStrings(RegistryFriendlyByteBuf buffer, List<String> values) {
        buffer.writeVarInt(values.size());
        for (String value : values) {
            buffer.writeUtf(value);
        }
    }

    private static List<String> readStrings(RegistryFriendlyByteBuf buffer) {
        int size = buffer.readVarInt();
        List<String> values = new java.util.ArrayList<>(size);
        for (int index = 0; index < size; index++) {
            values.add(buffer.readUtf());
        }
        return values;
    }
}
