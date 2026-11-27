import battle.BattleScene;
import boss.BossRegistry;
import core.Game;
import core.GlobalState;
import core.InputHandler;
import core.Scene;
import java.awt.Graphics2D;
import java.util.Random;

/** Launches one encounter in the player's existing local installation. */
public final class ChesscadeEncounter implements Scene {
    private final Game game = new Game();
    private final GlobalState stats = GlobalState.get();
    private final BattleScene battle;
    private boolean abandoned;

    private ChesscadeEncounter(long seed, String choice) {
        int[] groups = {BossRegistry.TORIEL, BossRegistry.PAPYRUS, BossRegistry.SANS,
                        BossRegistry.ASGORE, BossRegistry.UNDYNE, BossRegistry.MUFFET,
                        BossRegistry.METTATON_EX, BossRegistry.ASRIEL};
        stats.newGame();
        stats.maxhp = stats.hp = 40;
        int group = groups[new Random(seed).nextInt(groups.length)];
        if (!choice.isEmpty()) {
            group = switch (choice) {
                case "toriel" -> BossRegistry.TORIEL;
                case "papyrus" -> BossRegistry.PAPYRUS;
                case "sans" -> BossRegistry.SANS;
                case "asgore" -> BossRegistry.ASGORE;
                case "undyne", "undying" -> BossRegistry.UNDYNE;
                case "muffet" -> BossRegistry.MUFFET;
                case "ex" -> BossRegistry.METTATON_EX;
                case "neo" -> BossRegistry.METTATON_NEO;
                case "asriel" -> BossRegistry.ASRIEL;
                default -> throw new IllegalArgumentException(choice);
            };
            if (choice.equals("undying") || choice.equals("neo")) {
                stats.murderlv = stats.lv = 20;
                stats.at = 40;
                stats.osflavor = 1;
            }
        }
        battle = new BattleScene(game, game.input(), group);
    }

    public void update() {
        // Check before the upstream scene can revive the player on its next tick.
        if (stats.hp <= 0) {
            exit();
            return;
        }
        abandoned = game.input().pressed(InputHandler.Key.RESTART);
        battle.update();
    }

    public void render(Graphics2D graphics) {
        battle.render(graphics);
    }

    public void exit() {
        battle.exit();
        System.exit(stats.hp > 0 && !abandoned ? 10 : 11);
    }

    public static void main(String[] args) {
        ChesscadeEncounter encounter = new ChesscadeEncounter(Long.parseLong(args[0]), args.length > 1 ? args[1] : "");
        encounter.game.setScene(encounter);
        encounter.game.start("Chesscade / Undertale Boss Fight");
    }
}
