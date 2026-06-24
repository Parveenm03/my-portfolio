import arcade
import random
import math

WIDTH  = 800
HEIGHT = 600
TITLE  = "Space Shooter"

PLAYER_SPEED  = 5
BULLET_SPEED  = 12
ENEMY_SPEED   = 2


# ---------------------------------------------------------------------------
# Sci-fi beep / synth music using arcade's built-in synthesis (no file needed)
# ---------------------------------------------------------------------------
def make_sci_fi_music():
    """Return a short looping sci-fi synth track as an arcade.Sound."""
    try:
        import numpy as np
        import arcade.sound as _snd

        sr   = 22050          # sample rate
        dur  = 4.0            # seconds per loop
        t    = np.linspace(0, dur, int(sr * dur), endpoint=False)

        # --- bass pulse (low saw wave) ---
        freq_bass = 55        # A1
        bass = 0.25 * (2 * (t * freq_bass % 1) - 1)   # sawtooth

        # --- arpeggio melody ---
        notes = [220, 277, 330, 415,  330, 277, 220, 165]   # Am pentatonic ish
        note_len = dur / len(notes)
        melody = np.zeros_like(t)
        for i, f in enumerate(notes):
            mask = (t >= i * note_len) & (t < (i + 1) * note_len)
            local_t = t[mask] - i * note_len
            # square wave for that 8-bit feel
            melody[mask] = 0.15 * np.sign(np.sin(2 * math.pi * f * local_t))
            # quick attack/decay envelope
            env = np.minimum(local_t / 0.02, 1.0) * np.maximum(1 - local_t / note_len, 0.0)
            melody[mask] *= env

        # --- hi-hat tick every 0.25 s ---
        noise   = np.random.uniform(-1, 1, len(t))
        hat_env = np.zeros_like(t)
        for tick in np.arange(0, dur, 0.25):
            hat_env += np.exp(-200 * np.maximum(t - tick, 0)) * (t >= tick)
        hihat = 0.04 * noise * hat_env

        wave = bass + melody + hihat
        # Normalise
        peak = np.max(np.abs(wave))
        if peak > 0:
            wave = wave / peak * 0.7

        # Convert to 16-bit PCM bytes
        pcm = (wave * 32767).astype(np.int16).tobytes()

        import io, wave as wavemod
        buf = io.BytesIO()
        with wavemod.open(buf, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm)
        buf.seek(0)

        return arcade.load_sound(buf)
    except Exception:
        return None


class Game(arcade.Window):

    def __init__(self):
        super().__init__(WIDTH, HEIGHT, TITLE)
        arcade.set_background_color(arcade.color.BLACK)

        self.player        = None
        self.bullets       = []
        self.explosions    = []
        self.enemies       = []
        self.enemy_bullets = []
        self.score         = 0
        self.lives         = 3
        self.hit_cooldown  = 0
        self.left_pressed  = False
        self.right_pressed = False
        self.up_pressed    = False
        self.down_pressed  = False
        self.space_pressed = False
        self.fire_timer    = 0
        self.game_time          = 0      # global timer for twinkling

        # Try user's file first, then generated synth
        try:
            self.music = arcade.load_sound("music.mp3")
        except Exception:
            self.music = make_sci_fi_music()

        self.music_player = None

        # HUD text objects (created once — no PerformanceWarning)
        self.score_text     = arcade.Text("Score: 0",          10, 560, arcade.color.CYAN,        20)
        self.lives_text     = arcade.Text("Lives: 3",          10, 530, arcade.color.LIGHT_GREEN,  20)
        self.game_over_text = arcade.Text(
            "GAME  OVER\nPress R to Restart",
            WIDTH // 2, HEIGHT // 2,
            arcade.color.RED, 36,
            anchor_x="center", anchor_y="center",
            multiline=True, width=500
        )

    # ------------------------------------------------------------------
    def setup(self):
        self.player = arcade.SpriteSolidColor(50, 60, arcade.color.WHITE)
        self.player.center_x = WIDTH // 2
        self.player.center_y = 60

        self.score        = 0
        self.lives        = 3
        self.hit_cooldown = 0
        self.game_time         = 0

        self.bullets.clear()
        self.enemies.clear()
        self.enemy_bullets.clear()
        self.explosions.clear()

        # ---- Starfield: small + large stars with random brightness ----
        self.stars = []
        for _ in range(120):
            self.stars.append({
                "x":    random.randint(0, WIDTH),
                "y":    random.randint(0, HEIGHT),
                "r":    random.choice([1, 1, 1, 2, 2, 3]),   # radius
                "base": random.uniform(0.4, 1.0),            # base brightness
                "spd":  random.uniform(0.5, 2.5),            # scroll speed
                "phase": random.uniform(0, math.pi * 2),     # twinkle phase
            })

        # ---- Nebula blobs (static, drawn once as colour circles) ----
        self.nebulas = []
        for _ in range(6):
            self.nebulas.append({
                "x": random.randint(50, WIDTH  - 50),
                "y": random.randint(50, HEIGHT - 50),
                "r": random.randint(60, 140),
                "color": random.choice([
                    (60,  0, 80,  40),   # purple
                    (0,  30, 80,  35),   # deep blue
                    (0,  60, 50,  30),   # teal
                ])
            })

        if self.music:
            if self.music_player:
                try:
                    self.music_player.pause()
                except Exception:
                    pass
            self.music_player = arcade.play_sound(self.music, volume=0.35, looping=True)

    # ------------------------------------------------------------------
    def on_draw(self):
        self.clear()

        # 1. Nebula blobs
        for neb in self.nebulas:
            r, g, b, a = neb["color"]
            arcade.draw_circle_filled(neb["x"], neb["y"], neb["r"],
                                      (r, g, b, a))

        # 2. Stars (twinkling)
        for s in self.stars:
            twinkle = 0.5 + 0.5 * math.sin(self.game_time * 3 + s["phase"])
            bright  = int(s["base"] * twinkle * 255)
            bright  = max(60, min(bright, 255))
            arcade.draw_circle_filled(s["x"], s["y"], s["r"],
                                      (bright, bright, bright))

        # ---- GAME OVER screen ----
        if self.lives <= 0:
            self.game_over_text.draw()
            return

        # 3. Player — cyan triangle spaceship with orange engine
        cx = self.player.center_x
        cy = self.player.center_y
        visible = (self.hit_cooldown <= 0) or (int(self.hit_cooldown * 8) % 2 == 0)
        if visible:
            # Main body
            arcade.draw_triangle_filled(
                cx,        cy + 30,   # nose
                cx - 22,   cy - 15,   # left wing
                cx + 22,   cy - 15,   # right wing
                arcade.color.CYAN
            )
            # Wing accents
            arcade.draw_triangle_filled(
                cx - 22, cy - 15,
                cx - 35, cy - 25,
                cx - 10, cy - 15,
                (0, 180, 220)
            )
            arcade.draw_triangle_filled(
                cx + 22, cy - 15,
                cx + 35, cy - 25,
                cx + 10, cy - 15,
                (0, 180, 220)
            )
            # Engine flame — flickers
            flame_h = 10 + int(6 * math.sin(self.game_time * 20))
            arcade.draw_triangle_filled(
                cx,        cy - 15,
                cx - 9,    cy - 15 - flame_h,
                cx + 9,    cy - 15 - flame_h,
                (255, 140, 0)
            )

        # 4. Player bullets — sharp upward triangles (bright green laser)
        for bullet in self.bullets:
            bx, by = bullet.center_x, bullet.center_y
            arcade.draw_triangle_filled(
                bx,     by + 14,
                bx - 4, by - 6,
                bx + 4, by - 6,
                arcade.color.LIME_GREEN
            )
            # glow dot
            arcade.draw_circle_filled(bx, by + 14, 3, arcade.color.WHITE)

        # 5. Enemy bullets — small red downward triangles
        for eb in self.enemy_bullets:
            ex, ey = eb.center_x, eb.center_y
            arcade.draw_triangle_filled(
                ex,     ey - 10,   # tip (downward)
                ex - 4, ey + 5,
                ex + 4, ey + 5,
                arcade.color.RED
            )

        # 6. Enemies — inverted red/orange triangle (alien ships)
        for enemy in self.enemies:
            ex, ey = enemy.center_x, enemy.center_y
            # Body (inverted triangle — nose pointing DOWN)
            arcade.draw_triangle_filled(
                ex,        ey - 20,   # bottom tip
                ex - 22,   ey + 15,   # top-left
                ex + 22,   ey + 15,   # top-right
                arcade.color.RED
            )
            # Wing accents
            arcade.draw_triangle_filled(
                ex - 22, ey + 15,
                ex - 35, ey + 22,
                ex - 10, ey + 10,
                (180, 0, 0)
            )
            arcade.draw_triangle_filled(
                ex + 22, ey + 15,
                ex + 35, ey + 22,
                ex + 10, ey + 10,
                (180, 0, 0)
            )
            # Core glow
            arcade.draw_circle_filled(ex, ey, 6, (255, 80, 0))

        # 7. Explosions
        for exp in self.explosions:
            arcade.draw_circle_filled(exp["x"], exp["y"], exp["size"],
                                      (255, 140, 0, 180))
            arcade.draw_circle_filled(exp["x"], exp["y"], exp["size"] * 0.5,
                                      arcade.color.WHITE)

        # 8. HUD
        self.score_text.text = f"Score: {self.score}"
        self.lives_text.text = f"Lives: {'❤️ ' * self.lives}"
        self.score_text.draw()
        self.lives_text.draw()

    # ------------------------------------------------------------------
    def on_update(self, delta_time):
        self.game_time += delta_time

        if self.lives <= 0:
            return

        # Fire timer + shoot
        self.fire_timer += delta_time
        if self.space_pressed and self.fire_timer > 0.13:
            b = arcade.SpriteSolidColor(8, 20, arcade.color.LIME_GREEN)
            b.center_x = self.player.center_x
            b.center_y = self.player.center_y + 32
            self.bullets.append(b)
            self.fire_timer = 0

        # Move player
        if self.left_pressed:  self.player.center_x -= PLAYER_SPEED
        if self.right_pressed: self.player.center_x += PLAYER_SPEED
        if self.up_pressed:    self.player.center_y += PLAYER_SPEED
        if self.down_pressed:  self.player.center_y -= PLAYER_SPEED

        # Boundary clamp
        self.player.center_x = max(35, min(self.player.center_x, WIDTH  - 35))
        self.player.center_y = max(35, min(self.player.center_y, HEIGHT - 35))

        # Scroll stars
        for s in self.stars:
            s["y"] -= s["spd"]
            if s["y"] < 0:
                s["y"] = HEIGHT
                s["x"] = random.randint(0, WIDTH)

        # Move player bullets UP
        for b in self.bullets:
            b.center_y += BULLET_SPEED

        # Move enemies DOWN + occasional shoot
        for enemy in self.enemies[:]:
            enemy.center_y -= ENEMY_SPEED
            if random.randint(1, 120) == 1:
                eb = arcade.SpriteSolidColor(8, 16, arcade.color.RED)
                eb.center_x = enemy.center_x
                eb.center_y = enemy.center_y - 20
                self.enemy_bullets.append(eb)

        # Move enemy bullets DOWN
        for eb in self.enemy_bullets:
            eb.center_y -= 5

        # Invincibility cooldown
        if self.hit_cooldown > 0:
            self.hit_cooldown -= delta_time

        # ---- Player hit by enemy bullet ----
        if self.hit_cooldown <= 0:
            for eb in self.enemy_bullets[:]:
                if arcade.check_for_collision(eb, self.player):
                    self.enemy_bullets.remove(eb)
                    self.lives -= 1
                    self.hit_cooldown = 1.8
                    self.explosions.append({
                        "x": self.player.center_x,
                        "y": self.player.center_y,
                        "size": 8
                    })
                    break   # only 1 hit per frame

        # Grow / remove explosions
        for exp in self.explosions[:]:
            exp["size"] += 3
            if exp["size"] > 40:
                self.explosions.remove(exp)

        # Spawn enemies from TOP only (cleaner gameplay)
        if random.randint(1, 40) == 1:
            enemy = arcade.SpriteSolidColor(44, 44, arcade.color.RED)
            enemy.center_x = random.randint(30, WIDTH - 30)
            enemy.center_y = HEIGHT + 30
            self.enemies.append(enemy)

        # ---- Player bullet hits enemy ----
        for b in self.bullets[:]:
            for enemy in self.enemies[:]:
                if arcade.check_for_collision(b, enemy):
                    if b in self.bullets:
                        self.bullets.remove(b)
                    if enemy in self.enemies:
                        self.enemies.remove(enemy)
                    self.score += 1
                    self.explosions.append({
                        "x": enemy.center_x,
                        "y": enemy.center_y,
                        "size": 6
                    })
                    break

        # ---- Enemy directly touches player — lose life ----
        if self.hit_cooldown <= 0:
            for enemy in self.enemies[:]:
                if arcade.check_for_collision(enemy, self.player):
                    self.enemies.remove(enemy)
                    self.lives -= 1
                    self.hit_cooldown = 1.8
                    self.explosions.append({
                        "x": self.player.center_x,
                        "y": self.player.center_y,
                        "size": 8
                    })
                    break

        # Enemy passes bottom — just remove silently, NO life loss
        self.enemies       = [e  for e  in self.enemies        if e.center_y  > -60]

        # Cleanup off-screen objects
        self.bullets       = [b  for b  in self.bullets       if b.center_y  < HEIGHT + 20]
        self.enemy_bullets = [eb for eb in self.enemy_bullets if eb.center_y > -20]

    # ------------------------------------------------------------------
    def on_key_press(self, key, modifiers):
        if   key == arcade.key.LEFT:  self.left_pressed  = True
        elif key == arcade.key.RIGHT: self.right_pressed = True
        elif key == arcade.key.UP:    self.up_pressed    = True
        elif key == arcade.key.DOWN:  self.down_pressed  = True
        elif key == arcade.key.SPACE: self.space_pressed = True
        elif key == arcade.key.R:     self.setup()

    def on_key_release(self, key, modifiers):
        if   key == arcade.key.LEFT:  self.left_pressed  = False
        elif key == arcade.key.RIGHT: self.right_pressed = False
        elif key == arcade.key.UP:    self.up_pressed    = False
        elif key == arcade.key.DOWN:  self.down_pressed  = False
        elif key == arcade.key.SPACE: self.space_pressed = False


def main():
    game = Game()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()
