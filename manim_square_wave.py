"""
manim_square_wave.py
====================
Apresentacao Manim ANALOGA a do surto, porem para uma ONDA QUADRADA (PWM) de
20 kHz aplicada a MESMA bobina (enrolamento de gerador, neutro aterrado, com
capacitancia serie, alpha = 5).

Ideia central: cada BORDA da onda quadrada e um mini-surto. A frente rapida
concentra a tensao na entrada exatamente como o impulso 1,2/50 us
(distribuicao sinh(alpha(1-x))/sinh(alpha)); a diferenca e a REPETICAO -- a
concentracao se repete a cada borda, 40 000 x/s, estressando o isolamento de
entrada em maquinas alimentadas por inversor.

Reutiliza VisualFactory / cores de manim_presentation.py (sem modifica-lo).
O trabalho do surto (SurgePresentation) permanece intacto.

    manim -ql manim_square_wave.py SquareWavePresentation     # previa rapida
    manim manim_square_wave.py SquareWavePresentation         # 1080p60 (manim.cfg)
"""
from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO

import numpy as np
from manim import *

from manim_presentation import (
    SurgePresentation, VisualFactory,
    BACKGROUND, PANEL_STROKE, TEXT, MUTED, BLUE, CYAN, ORANGE,
    GREEN, YELLOW, PURPLE, TIME_DOMAIN_ALPHA, CONFIG_PATH,
    WIDE_GRAPH_X_LENGTH,
)
from src.models.distributed_coil import DistributedCoil
from src.solvers.time_domain_solver import TimeDomainSolver
from src.sources.impulse_source import ImpulseSource
from src.utils.simulation_config import SimulationConfig

# ---- parametros da onda quadrada PWM -------------------------------------
SQUARE_FREQ_HZ = 20_000.0     # 20 kHz  -> periodo T = 50 us
SQUARE_T_RISE_S = 0.2e-6      # tempo de borda (dv/dt = A/t_rise)
SQUARE_WINDOW_US = 150.0      # 3 periodos
SQUARE_DT_S = 5e-8            # passo de reporte (50 ns)
EVOLUTION_RUN_TIME_S = 48.0   # varredura temporal: 48 s p/ 150 us a 60 fps =>
                              # ~52 ns/frame ~= 1 ponto da simulacao (50 ns) por frame
ALPHA = TIME_DOMAIN_ALPHA     # 5 (mesmo da bobina do surto aterrado)


def simulate_square():
    """Simula a bobina aterrada (com cap. serie, alpha=5) sob onda quadrada 20 kHz."""
    base = SimulationConfig.from_json(str(CONFIG_PATH))
    cfg = base.copy_with(
        model_type="pi",
        termination="grounded",
        source_type="square",
        t_front=SQUARE_T_RISE_S,
        t_total=SQUARE_WINDOW_US * 1e-6,
        dt=SQUARE_DT_S,
        C_series_total=base.C_total / (ALPHA ** 2),
    )
    source = ImpulseSource(
        source_type="square",
        amplitude=cfg.V_amplitude,
        t_front=SQUARE_T_RISE_S,
        frequency=SQUARE_FREQ_HZ,
    )
    coil = DistributedCoil(cfg)
    with redirect_stdout(StringIO()):
        results = TimeDomainSolver(coil, source, cfg).solve()
    return results, cfg, source


class SquareWavePresentation(SurgePresentation):
    """PWM square wave (20 kHz) hitting a winding -- the repetitive-surge story."""

    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.factory = VisualFactory()
        self.results, self.cfg, self.source = simulate_square()

        self.intro_source_scene()
        self.circuit_scene()
        self.per_edge_scene()
        self.evolution_scene()
        self.conclusion_scene()

    # ------------------------------------------------------------------
    # 1. Intro + source (slides 1+2 fundidos): a 20 kHz PWM square wave
    # ------------------------------------------------------------------
    def intro_source_scene(self) -> None:
        heading = self.factory.heading(
            "PWM Square Wave on a Winding",
            "The output of a PWM inverter: every switching edge is a surge",
        )

        facts = VGroup(
            MathTex(r"f = 20\,\mathrm{kHz}", font_size=30, color=CYAN),
            MathTex(r"T = 1/f = 50\,\mu\mathrm{s}", font_size=30, color=CYAN),
            MathTex(r"\frac{dv}{dt} = \frac{V}{t_r},\ \ t_r = 0.2\,\mu\mathrm{s}",
                    font_size=30, color=YELLOW),
        ).arrange(RIGHT, buff=0.85)
        facts.next_to(heading, DOWN, buff=0.32)

        t_us = np.linspace(0, 2.5 * 50.0, 4000)          # 2.5 periodos, em us
        v = self.source.evaluate_array(t_us * 1e-6)
        axes = Axes(
            x_range=[0, 125, 25], y_range=[0, 1100, 250],
            x_length=10.4, y_length=3.3,
            axis_config={"color": MUTED, "stroke_width": 2},
            tips=False,
        ).next_to(facts, DOWN, buff=0.6)
        x_label = MathTex(r"t\;(\mu\mathrm{s})", font_size=24, color=MUTED)
        x_label.next_to(axes.x_axis.get_end(), DOWN, buff=0.18)
        y_label = MathTex(r"v_s\;(\mathrm{V})", font_size=24, color=MUTED)
        y_label.next_to(axes.y_axis.get_top(), UP, buff=0.1)
        graph = self.factory.line_graph(axes, t_us, v, ORANGE, 3.0)

        self.play(FadeIn(heading, shift=DOWN * 0.15), run_time=1.0)
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label), run_time=0.9)
        self.play(Create(graph), run_time=1.8)
        self.play(FadeIn(facts), run_time=0.8)
        self.wait(1.3)
        self.clear()

    # ------------------------------------------------------------------
    # 3. Circuit (same grounded ladder)
    # ------------------------------------------------------------------
    def circuit_scene(self) -> None:
        heading = self.factory.heading(
            "Same Winding, Same Circuit",
            "Grounded ladder with shunt and turn-to-turn capacitance",
        )
        ladder = self.factory.tikz_ladder(termination="grounded")
        ladder.scale_to_fit_width(11.0).shift(DOWN * 0.3)
        note = MathTex(
            r"\alpha = \sqrt{C_g / C_s} = 5",
            font_size=34, color=CYAN,
        ).next_to(ladder, DOWN, buff=0.5)
        self.play(FadeIn(heading), run_time=0.8)
        self.play(FadeIn(ladder, shift=UP * 0.2), run_time=1.2)
        self.play(FadeIn(note), run_time=0.6)
        self.wait(1.2)
        self.clear()

    # ------------------------------------------------------------------
    # 4. One edge = one surge (the initial sinh distribution)
    # ------------------------------------------------------------------
    def per_edge_scene(self) -> None:
        heading = self.factory.heading(
            "One Edge = One Surge",
            "At every edge the voltage crowds onto the entrance turns",
        )

        coil = DistributedCoil(self.cfg)
        x, v = coil.initial_voltage_distribution(v_input=1.0)   # alpha=5, aterrado

        formula = MathTex(
            r"\frac{v(x)}{V_0} = \frac{\sinh\!\big(\alpha(1-x)\big)}{\sinh(\alpha)},"
            r"\quad \alpha = 5",
            font_size=30, color=TEXT,
        ).next_to(heading, DOWN, buff=0.28)

        axes = Axes(
            x_range=[0, 100, 25], y_range=[0, 105, 25],
            x_length=10.0, y_length=3.2,
            axis_config={"color": MUTED, "stroke_width": 2},
            tips=False,
        ).next_to(formula, DOWN, buff=0.5)
        x_label = MathTex(r"x_{\mathrm{coil}}\;(\%)", font_size=24, color=MUTED)
        x_label.next_to(axes.x_axis.get_end(), DOWN, buff=0.18)
        y_label = MathTex(r"v/V_0\;(\%)", font_size=24, color=MUTED)
        y_label.next_to(axes.y_axis.get_top(), UP, buff=0.1)

        sinh_curve = self.factory.line_graph(axes, x * 100, v * 100, GREEN, 3.4)
        uniform = DashedLine(
            axes.c2p(0, 100), axes.c2p(100, 0), color=MUTED, stroke_width=2,
        )
        uni_label = Text("uniform (low-frequency guess)", font_size=18, color=MUTED)
        uni_label.next_to(axes.c2p(64, 38), UR, buff=0.05)
        entrance = Text("entrance turns carry most of it", font_size=20, color=ORANGE)
        entrance.next_to(axes.c2p(20, 72), UR, buff=0.1)

        self.play(FadeIn(heading), FadeIn(formula), run_time=1.0)
        self.play(Create(axes), FadeIn(x_label), FadeIn(y_label), run_time=0.8)
        self.play(Create(uniform), FadeIn(uni_label), run_time=0.8)
        self.play(Create(sinh_curve), run_time=1.6)
        self.play(FadeIn(entrance, shift=UP * 0.1), run_time=0.8)
        self.wait(1.4)
        self.clear()

    # ------------------------------------------------------------------
    # 5. Time evolution under the pulse train (main animation)
    # ------------------------------------------------------------------
    def evolution_scene(self) -> None:
        heading = self.factory.heading(
            "Under the Pulse Train",
            "Each edge re-crowds the entrance, then it relaxes -- repeatedly",
        )

        t = self.results["t"]                                    # s
        V = np.asarray(self.results["V_nodes"], dtype=float)     # (n_nodes, n_time)
        pos = np.asarray(self.results["positions"], dtype=float)
        end_us = float(t[-1] * 1e6)

        y_limit = max(1100.0, float(np.ceil(np.max(np.abs(V)) / 500.0) * 500.0))
        y_step = 500.0 if y_limit <= 2500.0 else 1000.0
        axes = Axes(
            x_range=[0, 100, 20],
            y_range=[-y_limit, y_limit, y_step],
            x_length=WIDE_GRAPH_X_LENGTH,
            y_length=3.25,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).shift(UP * 0.05)
        x_label = MathTex(r"x_{\mathrm{coil}}\;(\%)", font_size=22, color=MUTED)
        x_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.14)
        y_label = MathTex(r"v\;(\mathrm{V})", font_size=22, color=MUTED)
        y_label.move_to(axes.c2p(6.0, y_limit * 0.92))
        labels = VGroup(x_label, y_label)
        tracker = ValueTracker(0.0)

        def current_profile() -> np.ndarray:
            ts = tracker.get_value() * 1e-6
            return np.asarray(
                [np.interp(ts, t, V[i]) for i in range(V.shape[0])], dtype=float
            )

        def make_profile() -> VGroup:
            y = current_profile()
            x = pos * 100.0
            line = self.factory.line_graph(axes, x, y, GREEN, width=4.0)
            dots = VGroup(*[
                Dot(axes.c2p(float(xx), float(yy)), radius=0.045,
                    color=self.voltage_color(float(yy)))
                for xx, yy in zip(x, y)
            ])
            return VGroup(line, dots)
        profile = always_redraw(make_profile)

        def make_uniform_ref() -> VMobject:
            v_in = float(current_profile()[0])
            ref = self.factory.line_graph(
                axes, np.array([0.0, 100.0]), np.array([v_in, 0.0]), MUTED, width=2.0,
            )
            return DashedVMobject(ref, num_dashes=26)
        uniform_ref = always_redraw(make_uniform_ref)

        # barras dinamicas da queda de tensao local entre nos (mesma da apresentacao do surto)
        percentage_row = self.make_dynamic_local_percentage_row(
            axes, pos, current_profile, y_limit, "grounded local dV (%)",
        )

        time_symbol = MathTex("t =", font_size=28, color=YELLOW)
        time_value = DecimalNumber(0, num_decimal_places=1, font_size=22, color=YELLOW)
        time_unit = MathTex(r"\mu\mathrm{s}", font_size=28, color=YELLOW)
        time_label = VGroup(time_symbol, time_value, time_unit).arrange(RIGHT, buff=0.08)
        time_label.to_corner(UR, buff=0.55)

        def update_time_label(group: VGroup) -> VGroup:
            time_value.set_value(tracker.get_value())
            group.arrange(RIGHT, buff=0.08)
            group.to_corner(UR, buff=0.55)
            return group
        time_label.add_updater(update_time_label)

        ground_dot = Dot(axes.c2p(100.0, 0.0), radius=0.07, color=GREEN)
        ground_label = Text("end tied to reference", font_size=15, color=GREEN)
        ground_label.move_to(axes.c2p(78.0, -y_limit * 0.36))
        ground_leader = Line(
            ground_label.get_right() + RIGHT * 0.08 + UP * 0.02,
            ground_dot.get_center() + LEFT * 0.12,
            color=GREEN, stroke_width=2.0,
        )
        ground_marker = VGroup(ground_dot, ground_leader, ground_label)
        alpha_label = MathTex(rf"\alpha = {ALPHA:.0f}", font_size=20, color=CYAN)
        alpha_label.move_to(axes.c2p(13.0, y_limit * 0.72))

        self.play(FadeIn(heading), Create(axes), FadeIn(labels), run_time=1.0)
        self.play(
            FadeIn(uniform_ref), FadeIn(profile), FadeIn(percentage_row),
            FadeIn(time_label), FadeIn(ground_marker), FadeIn(alpha_label),
            run_time=0.8,
        )
        # animacao lenta (48 s para a mesma janela de 150 us): ~52 ns/frame,
        # cerca de um ponto da simulacao (dt=50 ns) por frame de video
        self.play(
            tracker.animate.set_value(end_us),
            run_time=EVOLUTION_RUN_TIME_S, rate_func=linear,
        )
        self.wait(0.6)
        self.clear()

    # ------------------------------------------------------------------
    # 6. Conclusion
    # ------------------------------------------------------------------
    def conclusion_scene(self) -> None:
        heading = self.factory.heading(
            "Why It Matters: Inverter-Fed Insulation",
            "Repetitive switching stress on the entrance-turn insulation",
        )

        bullets = VGroup(
            Tex(r"$\bullet$~Every PWM edge crowds the voltage onto the first turns "
                r"($\alpha = 5$).", font_size=32, color=TEXT),
            Tex(r"$\bullet$~The impulse does it once; the $20\,$kHz square wave does it "
                r"$40\,000\times/\mathrm{s}$.", font_size=32, color=TEXT),
            Tex(r"$\bullet$~This repetitive $dv/dt$ stress ages the entrance-turn "
                r"insulation.", font_size=32, color=TEXT),
            Tex(r"$\bullet$~Mitigation: $dv/dt$ filters, short cables, reinforced "
                r"entrance insulation.", font_size=32, color=GREEN),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.5).next_to(heading, DOWN, buff=0.8)
        for line in bullets:
            if line.width > 12.2:
                line.scale_to_fit_width(12.2)
        bullets.next_to(heading, DOWN, buff=0.8).to_edge(LEFT, buff=0.9)

        self.play(FadeIn(heading), run_time=0.8)
        for line in bullets:
            self.play(FadeIn(line, shift=RIGHT * 0.15), run_time=0.6)
        self.wait(1.6)
        self.clear()


# ----------------------------------------------------------------------
# Cenas standalone para previa rapida (espelham as do surto)
# ----------------------------------------------------------------------
class SquareSourceScene(SquareWavePresentation):
    """Apenas o slide de abertura+fonte: manim -ql manim_square_wave.py SquareSourceScene"""

    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.factory = VisualFactory()
        self.results, self.cfg, self.source = simulate_square()
        self.intro_source_scene()


class SquareEvolutionPreview(SquareWavePresentation):
    """Apenas a evolucao temporal: manim -ql manim_square_wave.py SquareEvolutionPreview"""

    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.factory = VisualFactory()
        self.results, self.cfg, self.source = simulate_square()
        self.evolution_scene()
