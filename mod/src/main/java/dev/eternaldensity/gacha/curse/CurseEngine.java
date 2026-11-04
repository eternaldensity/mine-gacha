package dev.eternaldensity.gacha.curse;

import com.mojang.serialization.Dynamic;
import dev.eternaldensity.gacha.GachaAttachments;
import dev.eternaldensity.gacha.GachaMod;
import dev.eternaldensity.gacha.GachaRegistries;
import dev.eternaldensity.gacha.PlayerData;
import dev.eternaldensity.gacha.curse.Curse;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.TagKey;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.MobSpawnType;
import net.minecraft.world.entity.ai.attributes.Attribute;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.neoforged.neoforge.common.util.TriState;
import net.neoforged.neoforge.event.entity.living.LivingEntityUseItemEvent;
import net.neoforged.neoforge.event.entity.player.AdvancementEvent;
import net.neoforged.neoforge.event.entity.player.ItemEntityPickupEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.tick.PlayerTickEvent;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.Optional;

/**
 * Curse engine (PROJECT_PLAN.md section 6.8). Three flat slots; resolving frees
 * one. Persisted through the player attachment. Only advancement-based resolves
 * and attribute/effect hooks are implemented in this build; inventory, mob and
 * event hooks are declared in the schema and logged as unsupported.
 */
public final class CurseEngine {
    public static final int MAX_SLOTS = 3;

    private CurseEngine() {
    }

    public static void register() {
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onAdvancementEarned);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onRightClickItem);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onRightClickBlock);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onLeftClickBlock);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onUseItemStart);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onPickup);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onPlayerTick);
    }

    public static boolean takeCurse(ServerPlayer player, String curseId) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().size() >= MAX_SLOTS) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal(
                    "All " + MAX_SLOTS + " curse slots are full."), false);
            return false;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
        if (curse == null) {
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Unknown curse: " + curseId), false);
            return false;
        }
        if (applyHook(player, curseId, curse)) {
            List<String> curses = new ArrayList<>(state.curses());
            curses.add(curseId);
            PlayerData updated = new PlayerData(
                    state.ownedEntries(), state.lostEntries(), state.grantedFeats(),
                    state.residue(), state.modules(), curses, state.rngSeed(), state.powerScore());
            player.setData(GachaAttachments.PLAYER_DATA.get(), updated);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal(
                    "Curse taken: " + curse.name() + " (" + state.curses().size() + "/" + MAX_SLOTS + " slots)"), false);
            return true;
        }
        return false;
    }

    public static boolean resolveCurse(ServerPlayer player, String curseId) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (!state.curses().contains(curseId)) {
            return false;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
        if (curse == null) return false;
        unapplyHook(player, curseId, curse);
        List<String> curses = new ArrayList<>(state.curses());
        curses.remove(curseId);
        PlayerData updated = new PlayerData(
                state.ownedEntries(), state.lostEntries(), state.grantedFeats(),
                state.residue(), state.modules(), curses, state.rngSeed(), state.powerScore());
        player.setData(GachaAttachments.PLAYER_DATA.get(), updated);
        player.displayClientMessage(net.minecraft.network.chat.Component.literal("Curse resolved: " + curse.name()), false);
        return true;
    }

    private static void onAdvancementEarned(AdvancementEvent.AdvancementEarnEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) return;
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        List<String> toResolve = new ArrayList<>();
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse == null) continue;
            Dynamic<?> resolve = curse.resolve();
            if ("advancement".equals(resolve.get("type").asString(""))) {
                String adv = resolve.get("advancement").asString("");
                if (adv.equals(event.getAdvancement().id().toString())) {
                    toResolve.add(curseId);
                }
            }
        }
        for (String curseId : toResolve) {
            resolveCurse(player, curseId);
        }
    }

    private static void onRightClickItem(PlayerInteractEvent.RightClickItem event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            String mode = denial(player, event.getItemStack(), "use", "hold");
            if (mode != null) {
                event.setCanceled(true);
                denyMessage(player, mode, event.getItemStack());
            }
        }
    }

    private static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            String mode = denial(player, event.getItemStack(), "use", "hold");
            if (mode != null) {
                event.setCanceled(true);
                denyMessage(player, mode, event.getItemStack());
            }
        }
    }

    private static void onLeftClickBlock(PlayerInteractEvent.LeftClickBlock event) {
        if (event.getEntity() instanceof ServerPlayer player) {
            String mode = denial(player, event.getItemStack(), "hold");
            if (mode != null) {
                event.setCanceled(true);
                denyMessage(player, mode, event.getItemStack());
            }
        }
    }

    private static void onUseItemStart(LivingEntityUseItemEvent.Start event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        ItemStack stack = event.getItem();
        String mode = denial(player, stack, "use", "hold");
        if (mode == null && (stack.has(net.minecraft.core.component.DataComponents.FOOD)
                || stack.is(Items.POTION) || stack.is(Items.MILK_BUCKET))) {
            mode = denial(player, stack, "consume");
        }
        if (mode != null) {
            event.setCanceled(true);
            denyMessage(player, mode, stack);
        }
    }

    private static void onPickup(ItemEntityPickupEvent.Pre event) {
        if (event.getPlayer() instanceof ServerPlayer player) {
            ItemStack stack = event.getItemEntity().getItem();
            if (denial(player, stack, "pickup") != null) {
                event.setCanPickup(TriState.FALSE);
                denyMessage(player, "pickup", stack);
            }
        }
    }

    private static void onPlayerTick(PlayerTickEvent.Post event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().isEmpty()) {
            return;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse == null || curse.mature()) {
                continue;
            }
            Dynamic<?> hook = curse.hook();
            if (!"mob".equals(hook.get("type").asString(""))) {
                continue;
            }
            int interval = Math.max(20, hook.get("interval").asInt(200));
            if (player.tickCount % interval != 0) {
                continue;
            }
            List<ResourceLocation> entities = hook.get("entities").asStream()
                    .map(value -> ResourceLocation.tryParse(value.asString("")))
                    .filter(Objects::nonNull)
                    .toList();
            if (entities.isEmpty()) {
                continue;
            }
            String behavior = hook.get("behavior").asString("target");
            if ("spawn".equals(behavior)) {
                int count = Math.max(1, hook.get("count").asInt(1));
                for (int index = 0; index < count; index++) {
                    ResourceLocation entityId = entities.get(player.getRandom().nextInt(entities.size()));
                    var type = BuiltInRegistries.ENTITY_TYPE.getOptional(entityId).orElse(null);
                    if (type == null) {
                        continue;
                    }
                    BlockPos pos = player.blockPosition().offset(
                            player.getRandom().nextInt(9) - 4, 1, player.getRandom().nextInt(9) - 4);
                    type.spawn((net.minecraft.server.level.ServerLevel) player.level(), pos, MobSpawnType.EVENT);
                }
            } else if ("target".equals(behavior)) {
                for (Mob mob : player.level().getEntitiesOfClass(Mob.class, player.getBoundingBox().inflate(16))) {
                    if (entities.contains(BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()))) {
                        mob.setTarget(player);
                    }
                }
            }
        }
    }

    private static String denial(ServerPlayer player, ItemStack stack, String... modes) {
        if (stack.isEmpty()) {
            return null;
        }
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().isEmpty()) {
            return null;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse == null || curse.mature()) {
                continue;
            }
            Dynamic<?> hook = curse.hook();
            if (!"inventory".equals(hook.get("type").asString(""))) {
                continue;
            }
            String hookMode = hook.get("mode").asString("");
            boolean applies = false;
            for (String mode : modes) {
                if (mode.equals(hookMode)) {
                    applies = true;
                    break;
                }
            }
            if (!applies) {
                continue;
            }
            for (Dynamic<?> denied : hook.get("deny").asStream().toList()) {
                String value = denied.asString("");
                if (value.startsWith("#")) {
                    ResourceLocation id = ResourceLocation.tryParse(value.substring(1));
                    if (id != null && stack.is(TagKey.create(Registries.ITEM, id))) {
                        return hookMode;
                    }
                } else {
                    ResourceLocation id = ResourceLocation.tryParse(value);
                    if (id == null) {
                        continue;
                    }
                    Item item = BuiltInRegistries.ITEM.get(id);
                    if (item != null && stack.is(item)) {
                        return hookMode;
                    }
                }
            }
        }
        return null;
    }

    private static void denyMessage(ServerPlayer player, String mode, ItemStack stack) {
        String verb = switch (mode) {
            case "pickup" -> "picking up";
            case "consume" -> "consuming";
            default -> "using";
        };
        player.displayClientMessage(Component.literal(
                "A curse prevents you from " + verb + " " + stack.getHoverName().getString()), true);
    }

    private static boolean applyHook(ServerPlayer player, String curseId, Curse curse) {
        Dynamic<?> hook = curse.hook();
        String type = hook.get("type").asString("");
        return switch (type) {
            case "attribute" -> {
                applyAttribute(player, curseId, hook);
                yield true;
            }
            case "effect" -> {
                applyEffect(player, hook);
                yield true;
            }
            default -> {
                GachaMod.LOGGER.info("Curse {} hook type '{}' not yet implemented; curse occupies a slot anyway", curseId, type);
                yield true;
            }
        };
    }

    private static void unapplyHook(ServerPlayer player, String curseId, Curse curse) {
        Dynamic<?> hook = curse.hook();
        String type = hook.get("type").asString("");
        if ("attribute".equals(type)) {
            unapplyAttribute(player, curseId, hook);
        } else if ("effect".equals(type)) {
            ResourceLocation effectId = ResourceLocation.tryParse(hook.get("effect").asString(""));
            if (effectId != null) {
                BuiltInRegistries.MOB_EFFECT.getHolder(effectId)
                        .ifPresent(player::removeEffect);
            }
        }
    }

    /**
     * Reapply every owned curse hook after a login or respawn. Attribute
     * modifiers and infinite effects are transient entity state; the curse list
     * itself is persisted.
     */
    public static void reapplyCurseHooks(ServerPlayer player) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().isEmpty()) {
            return;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse != null && !curse.mature()) {
                applyHook(player, curseId, curse);
            }
        }
    }

    private static void applyAttribute(ServerPlayer player, String curseId, Dynamic<?> hook) {
        ResourceLocation attributeId = ResourceLocation.tryParse(hook.get("attribute").asString(""));
        if (attributeId == null) return;
        var attribute = BuiltInRegistries.ATTRIBUTE.getHolder(attributeId).orElse(null);
        if (attribute == null) return;
        var instance = player.getAttribute(attribute);
        if (instance == null) return;
        AttributeModifier.Operation operation = switch (hook.get("operation").asString("add")) {
            case "multiply_base" -> AttributeModifier.Operation.ADD_MULTIPLIED_BASE;
            case "multiply_total" -> AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL;
            default -> AttributeModifier.Operation.ADD_VALUE;
        };
        double amount = hook.get("amount").asDouble(0.0);
        ResourceLocation modifierId = ResourceLocation.parse(curseId).withPrefix("curse/");
        instance.addTransientModifier(new AttributeModifier(modifierId, amount, operation));
    }

    private static void unapplyAttribute(ServerPlayer player, String curseId, Dynamic<?> hook) {
        ResourceLocation attributeId = ResourceLocation.tryParse(hook.get("attribute").asString(""));
        if (attributeId == null) return;
        var attribute = BuiltInRegistries.ATTRIBUTE.getHolder(attributeId).orElse(null);
        if (attribute == null) return;
        var instance = player.getAttribute(attribute);
        if (instance == null) return;
        ResourceLocation modifierId = ResourceLocation.parse(curseId).withPrefix("curse/");
        instance.removeModifier(modifierId);
    }

    private static void applyEffect(ServerPlayer player, Dynamic<?> hook) {
        ResourceLocation effectId = ResourceLocation.tryParse(hook.get("effect").asString(""));
        if (effectId == null) return;
        var effect = BuiltInRegistries.MOB_EFFECT.getHolder(effectId).orElse(null);
        if (effect == null) return;
        int amplifier = Math.max(0, hook.get("amplifier").asInt(0));
        player.addEffect(new MobEffectInstance(effect, MobEffectInstance.INFINITE_DURATION, amplifier));
    }
}
