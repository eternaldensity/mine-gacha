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
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
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
    private static final java.util.Map<java.util.UUID, java.util.Map<String, Integer>> KILL_PROGRESS = new java.util.concurrent.ConcurrentHashMap<>();

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
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onLivingDeath);
        net.neoforged.neoforge.common.NeoForge.EVENT_BUS.addListener(CurseEngine::onServerTick);
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


    private static void onLivingDeath(LivingDeathEvent event) {
        if (event.getEntity() instanceof ServerPlayer victim) {
            PlayerData vstate = victim.getData(GachaAttachments.PLAYER_DATA.get());
            if (!vstate.curses().isEmpty()) {
                Registry<Curse> vreg = victim.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
                for (String cid : vstate.curses()) {
                    Curse c = vreg.getOptional(ResourceLocation.parse(cid)).orElse(null);
                    if (c == null || c.mature()) continue;
                    Dynamic<?> h = c.hook();
                    if ("event".equals(h.get("type").asString("")) && "on_death".equals(h.get("event").asString(""))) {
                        // Apply configured effect on the killer? Just log; effect handled on respawn reapply.
                        GachaMod.LOGGER.info("Curse {} on_death triggered for {}", cid, victim.getName().getString());
                    }
                }
            }
        }
        if (!(event.getSource().getEntity() instanceof ServerPlayer player)) {
            return;
        }
        // Kill resolves and on_kill event hooks.
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().isEmpty()) {
            return;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        String victimId = BuiltInRegistries.ENTITY_TYPE.getKey(event.getEntity().getType()).toString();
        List<String> toResolve = new ArrayList<>();
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse == null || curse.mature()) {
                continue;
            }
            Dynamic<?> resolve = curse.resolve();
            if ("kill".equals(resolve.get("type").asString(""))) {
                String target = resolve.get("entity").asString("");
                int threshold = Math.max(1, resolve.get("count").asInt(1));
                if (!target.isEmpty() && (target.equals(victimId) || target.equals("*"))) {
                    java.util.Map<String, Integer> progress = KILL_PROGRESS
                            .computeIfAbsent(player.getUUID(), k -> new java.util.HashMap<>());
                    int next = progress.getOrDefault(curseId, 0) + 1;
                    progress.put(curseId, next);
                    if (next >= threshold) {
                        toResolve.add(curseId);
                    }
                }
            }
            Dynamic<?> hook = curse.hook();
            if ("event".equals(hook.get("type").asString("")) && "on_kill".equals(hook.get("event").asString(""))) {
                ResourceLocation effectId = ResourceLocation.tryParse(hook.get("params").get("effect").asString(""));
                if (effectId != null) {
                    BuiltInRegistries.MOB_EFFECT.getHolder(effectId).ifPresent(holder ->
                            player.addEffect(new MobEffectInstance(holder, 200, 0)));
                }
            }
        }
        for (String curseId : toResolve) {
            resolveCurse(player, curseId);
            KILL_PROGRESS.getOrDefault(player.getUUID(), java.util.Map.of()).remove(curseId);
        }
    }

    private static void onServerTick(net.neoforged.neoforge.event.tick.ServerTickEvent.Post event) {
        // Poll stat/collect/visit resolves for online players every 20 ticks.
        if (event.getServer().getTickCount() % 20 != 0) {
            return;
        }
        for (ServerPlayer player : event.getServer().getPlayerList().getPlayers()) {
            checkNonKillResolves(player);
        }
    }

    private static void checkNonKillResolves(ServerPlayer player) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().isEmpty()) {
            return;
        }
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        List<String> toResolve = new ArrayList<>();
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse == null || curse.mature()) {
                continue;
            }
            Dynamic<?> resolve = curse.resolve();
            String type = resolve.get("type").asString("");
            boolean met = false;
            if ("stat".equals(type)) {
                String stat = resolve.get("stat").asString("");
                double threshold = resolve.get("threshold").asDouble(0.0);
                double value = readStat(player, stat);
                met = value >= threshold && threshold > 0;
            } else if ("collect".equals(type)) {
                String item = resolve.get("item").asString("");
                int threshold = Math.max(1, resolve.get("count").asInt(1));
                int count = countItem(player, item);
                met = count >= threshold;
            } else if ("visit".equals(type)) {
                String location = resolve.get("location").asString("");
                met = atLocation(player, location);
            }
            if (met) {
                toResolve.add(curseId);
            }
        }
        for (String curseId : toResolve) {
            resolveCurse(player, curseId);
        }
    }

    private static double readStat(ServerPlayer player, String stat) {
        if (stat.isEmpty()) return 0.0;
        // Attribute-style stat: minecraft:generic.max_health etc.
        if (stat.startsWith("minecraft:generic.") || stat.startsWith("minecraft:")) {
            // try attribute
            try {
                ResourceLocation id = ResourceLocation.parse(stat);
                var holder = BuiltInRegistries.ATTRIBUTE.getHolder(id).orElse(null);
                if (holder != null) {
                    var inst = player.getAttribute(holder);
                    if (inst != null) return inst.getValue();
                }
            } catch (Exception ignored) {
            }
        }
        // Custom stat: minecraft:custom/minecraft.xxx
        try {
            if (stat.contains("/")) {
                String[] parts = stat.split("/", 2);
                ResourceLocation type = ResourceLocation.parse(parts[0]);
                ResourceLocation id = ResourceLocation.parse(parts[1]);
                net.minecraft.stats.StatType<?> statType = BuiltInRegistries.STAT_TYPE.get(type);
                if (statType != null) {
                    Object statObj = ((net.minecraft.stats.StatType<net.minecraft.resources.ResourceLocation>) statType).get(id);
                    if (statObj != null) {
                        return player.getStats().getValue((net.minecraft.stats.StatType) statType, statObj);
                    }
                }
            }
        } catch (Exception ignored) {
        }
        return 0.0;
    }

    private static int countItem(ServerPlayer player, String itemId) {
        if (itemId.isEmpty()) return 0;
        ResourceLocation id = ResourceLocation.tryParse(itemId);
        if (id == null) return 0;
        Item item = BuiltInRegistries.ITEM.get(id);
        if (item == null) return 0;
        int total = 0;
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack s = player.getInventory().getItem(i);
            if (!s.isEmpty() && s.is(item)) total += s.getCount();
        }
        return total;
    }

    private static boolean atLocation(ServerPlayer player, String location) {
        if (location.isEmpty()) return false;
        ResourceLocation id = ResourceLocation.tryParse(location);
        if (id == null) return false;
        // Dimension match
        if (player.level().dimension().location().equals(id)) {
            return true;
        }
        // Biome match
        try {
            var biome = player.level().getBiome(player.blockPosition());
            if (biome.unwrapKey().isPresent() && biome.unwrapKey().get().location().equals(id)) {
                return true;
            }
        } catch (Exception ignored) {
        }
        return false;
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
            case "event" -> {
                // Event hooks occupy a slot and are triggered by the event named
                // in the hook. They apply no persistent modifier on their own.
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
        } else if ("event".equals(type)) {
            // Nothing persistent to remove.
        }
    }

    /**
     * Reapply every owned curse hook after a login or respawn. Attribute
     * modifiers and infinite effects are transient entity state; the curse list
     * itself is persisted.
     */
    public static void triggerEvent(ServerPlayer player, String eventName) {
        PlayerData state = player.getData(GachaAttachments.PLAYER_DATA.get());
        if (state.curses().isEmpty()) return;
        Registry<Curse> registry = player.level().registryAccess().registryOrThrow(GachaRegistries.CURSE);
        for (String curseId : state.curses()) {
            Curse curse = registry.getOptional(ResourceLocation.parse(curseId)).orElse(null);
            if (curse == null || curse.mature()) continue;
            Dynamic<?> hook = curse.hook();
            if ("event".equals(hook.get("type").asString("")) && eventName.equals(hook.get("event").asString(""))) {
                ResourceLocation effectId = ResourceLocation.tryParse(hook.get("params").get("effect").asString(""));
                if (effectId != null) {
                    BuiltInRegistries.MOB_EFFECT.getHolder(effectId).ifPresent(holder ->
                            player.addEffect(new MobEffectInstance(holder, 200, 0)));
                }
            }
        }
    }

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
