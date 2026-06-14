"""
Professional Manim presentation for the distributed-coil surge project.

Run from the repository root:
    manim -pql --fps 15 manim_presentation.py SurgePresentation

The scene reads the real project outputs instead of hard-coding the main
simulation results. Regenerate those files first with:
    python main.py
    python scripts/compare_python_atp.py
"""

from __future__ import annotations

import csv
import json
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

import numpy as np
from manim import *

from src.models.distributed_coil import DistributedCoil
from src.solvers.time_domain_solver import TimeDomainSolver
from src.sources.impulse_source import ImpulseSource
from src.utils.simulation_config import SimulationConfig


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config" / "default_case.json"
PI_NODE_PATH = ROOT / "output" / "csv" / "node_voltages.csv"
PI_SCALARS_PATH = ROOT / "output" / "csv" / "summary_scalars.csv"
T_NODE_PATH = ROOT / "output" / "t_model" / "csv" / "node_voltages.csv"
T_SCALARS_PATH = ROOT / "output" / "t_model" / "csv" / "summary_scalars.csv"
GROUNDED_NODE_PATH = ROOT / "output" / "grounded" / "csv" / "node_voltages.csv"
GROUNDED_SCALARS_PATH = ROOT / "output" / "grounded" / "csv" / "summary_scalars.csv"
ATP_COMPARISON_PATH = ROOT / "output" / "atp" / "comparacao_python_atp.csv"
SOLENOID_IMAGE_PATH = ROOT / "assets" / "solenoid_reference.png"
LADDER_TIKZ_IMAGE_PATH = ROOT / "assets" / "tikz_ladder_circuit.png"
GROUNDED_LADDER_TIKZ_IMAGE_PATH = ROOT / "assets" / "tikz_ladder_grounded_circuit.png"
STATIC_TIME_WINDOW_US = 100.0
ANIMATION_TIME_WINDOW_US = 20.0
ANIMATION_PROFILE_RUN_TIME = 240.0
TIME_DOMAIN_ALPHA = 5.0  # winding distribution factor for the grounded time-domain
                         # animation (C_series_total = C_total / alpha^2): the surge
                         # starts crowded at the entrance and relaxes toward uniform.
PERCENT_SEGMENT_COUNT = 19
PERCENT_TOTAL_EPSILON = 1e-9
WIDE_GRAPH_X_LENGTH = 12.0
LOCAL_BAR_REFERENCE_PERCENT = 400.0
LOCAL_BAR_MAX_HEIGHT = 1.56
NATIVE_TEXT_FONT = "Arial"


BACKGROUND = "#10141c"
PANEL = "#18202b"
PANEL_STROKE = "#344258"
TEXT = "#f3f6fb"
MUTED = "#a9b4c2"
BLUE = "#4aa3ff"
CYAN = "#3ddbd9"
ORANGE = "#ffb454"
RED = "#ff5d73"
GREEN = "#6ee7a8"
YELLOW = "#ffd166"
PURPLE = "#a78bfa"

Text.set_default(font=NATIVE_TEXT_FONT)


@dataclass(frozen=True)
class NodeVoltageData:
    time_s: np.ndarray
    positions: np.ndarray
    voltages: np.ndarray
    labels: list[str]


@dataclass(frozen=True)
class ProjectData:
    config: dict
    pi_nodes: NodeVoltageData
    grounded_nodes: NodeVoltageData
    pi_scalars: dict[str, float]
    grounded_scalars: dict[str, float]


class ProjectDataLoader:
    """Loads the real project outputs used by the presentation."""

    required_files = (
        CONFIG_PATH,
    )

    def load(self) -> ProjectData:
        missing = [path for path in self.required_files if not path.exists()]
        if missing:
            missing_text = "\n".join(str(path) for path in missing)
            raise FileNotFoundError(
                "Required simulation outputs are missing:\n"
                f"{missing_text}\n\n"
                "Run from D:/surto-1 or check config/default_case.json."
            )

        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)

        pi_nodes, pi_scalars = self._simulate_manim_case(
            config,
            model_type="pi",
            termination="open",
        )
        grounded_nodes, grounded_scalars = self._simulate_manim_case(
            config,
            model_type="pi",
            termination="grounded",
            c_series_total=float(config["C_total"]) / (TIME_DOMAIN_ALPHA ** 2),
        )

        return ProjectData(
            config=config,
            pi_nodes=pi_nodes,
            grounded_nodes=grounded_nodes,
            pi_scalars=pi_scalars,
            grounded_scalars=grounded_scalars,
        )

    @staticmethod
    def _simulate_manim_case(
        config: dict,
        model_type: str,
        termination: str,
        c_series_total: float = 0.0,
    ) -> tuple[NodeVoltageData, dict[str, float]]:
        base_config = SimulationConfig(**config)
        manim_config = base_config.copy_with(
            model_type=model_type,
            termination=termination,
            t_total=ANIMATION_TIME_WINDOW_US * 1e-6,
            C_series_total=c_series_total,
        )
        source = ImpulseSource(
            source_type=manim_config.source_type,
            amplitude=manim_config.V_amplitude,
            t_front=manim_config.t_front,
            t_tail=manim_config.t_tail,
        )
        coil = DistributedCoil(manim_config)
        solver = TimeDomainSolver(coil, source, manim_config)
        with redirect_stdout(StringIO()):
            results = solver.solve()

        voltages = np.asarray(results["V_nodes"], dtype=float)
        positions = np.asarray(results["positions"], dtype=float)
        labels = ["V_source"] + [
            f"V_node_{index}"
            for index in range(1, voltages.shape[0])
        ]
        node_data = NodeVoltageData(
            time_s=np.asarray(results["t"], dtype=float),
            positions=positions,
            voltages=voltages,
            labels=labels,
        )
        return node_data, ProjectDataLoader._compute_scalars(node_data)

    @staticmethod
    def _compute_scalars(node_data: NodeVoltageData) -> dict[str, float]:
        v_peak_in = float(np.max(np.abs(node_data.voltages[0])))
        v_peak_out = float(np.max(np.abs(node_data.voltages[-1])))
        transfer_ratio = 0.0
        if v_peak_in > 0.0:
            transfer_ratio = v_peak_out / v_peak_in
        return {
            "transfer_ratio": transfer_ratio,
            "V_peak_in_V": v_peak_in,
            "V_peak_out_V": v_peak_out,
        }

    @staticmethod
    def _read_node_voltages(path: Path, model_type: str) -> NodeVoltageData:
        table = np.genfromtxt(path, delimiter=",", names=True)
        names = list(table.dtype.names or [])
        if "time_s" not in names or len(names) < 3:
            raise ValueError(f"Invalid node-voltage CSV: {path}")

        time_s = np.asarray(table["time_s"], dtype=float)
        labels = [name for name in names if name != "time_s"]
        voltages = np.vstack([np.asarray(table[name], dtype=float) for name in labels])

        if model_type == "pi":
            positions = np.linspace(0.0, 1.0, len(labels))
        else:
            n_sections = len(labels) - 2
            inner = (np.arange(n_sections, dtype=float) + 0.5) / float(n_sections)
            positions = np.concatenate(([0.0], inner, [1.0]))

        return NodeVoltageData(
            time_s=time_s,
            positions=positions,
            voltages=voltages,
            labels=labels,
        )

    @staticmethod
    def _read_scalars(path: Path) -> dict[str, float]:
        values: dict[str, float] = {}
        with path.open("r", encoding="utf-8", newline="") as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 2:
                    values[row[0]] = float(row[1])
        return values

    @staticmethod
    def _read_atp_comparison(path: Path) -> list[dict[str, float | str]]:
        filtered_lines: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            marker = line.strip().lstrip('"')
            if marker.startswith("#") or not marker:
                continue
            filtered_lines.append(line)

        if not filtered_lines:
            raise ValueError(f"Invalid ATP comparison CSV: {path}")

        rows: list[dict[str, float | str]] = []
        reader = csv.DictReader(filtered_lines)
        for row in reader:
            parsed: dict[str, float | str] = {}
            for key, value in row.items():
                if key == "node":
                    parsed[key] = str(value)
                elif value is not None and value != "":
                    parsed[key] = float(value)
            rows.append(parsed)
        return rows


class VisualFactory:
    """Reusable Manim components for the engineering presentation."""

    def heading(self, title: str, subtitle: str | None = None) -> VGroup:
        title_mob = Text(title, font_size=30, weight=BOLD, color=TEXT)
        title_mob.to_edge(UP, buff=0.28)
        line = Line(LEFT * 6.2, RIGHT * 6.2, color=PANEL_STROKE, stroke_width=2)
        line.next_to(title_mob, DOWN, buff=0.16)
        group = VGroup(title_mob, line)
        if subtitle:
            subtitle_mob = Text(subtitle, font_size=15, color=MUTED)
            subtitle_mob.next_to(line, DOWN, buff=0.12)
            group.add(subtitle_mob)
        return group

    def panel(self, width: float, height: float) -> RoundedRectangle:
        return RoundedRectangle(
            width=width,
            height=height,
            corner_radius=0.12,
            fill_color=PANEL,
            fill_opacity=0.94,
            stroke_color=PANEL_STROKE,
            stroke_width=1.5,
        )

    def coil(self, width: float = 5.8, height: float = 0.78, turns: int = 13) -> Group:
        if not SOLENOID_IMAGE_PATH.exists():
            raise FileNotFoundError(f"Missing solenoid image asset: {SOLENOID_IMAGE_PATH}")
        visual = ImageMobject(str(SOLENOID_IMAGE_PATH))
        visual.set_width(width)
        visual.set_z_index(2)
        guide_path = ParametricFunction(
            lambda u: np.array(
                [
                    -width / 2.0 + width * u,
                    height * 0.50 * np.sin(2.0 * np.pi * max(5, int(turns)) * u),
                    0.0,
                ]
            ),
            t_range=[0.0, 1.0],
            stroke_opacity=0.0,
        )
        return Group(visual, guide_path)

    def surge_arrow(self, text: str = "1.2/50 us surge") -> VGroup:
        arrow = Arrow(LEFT * 2.7, LEFT * 0.55, color=ORANGE, buff=0.0, stroke_width=7)
        label = Text(text, font_size=19, color=ORANGE, weight=BOLD)
        label.next_to(arrow, UP, buff=0.12)
        return VGroup(arrow, label)

    def ladder(self, sections: int = 20, width: float = 10.6) -> VGroup:
        group = VGroup()
        left_count = min(4, max(1, sections // 2))
        right_count = min(4, max(1, sections - left_count))
        left_nodes = np.linspace(-width / 2, -width * 0.14, left_count + 1)
        right_nodes = np.linspace(width * 0.14, width / 2, right_count + 1)
        x_values = np.concatenate((left_nodes, right_nodes))
        y_top = 0.35
        y_ground = -0.75

        ground_left = Line(
            np.array([left_nodes[0], y_ground, 0.0]),
            np.array([left_nodes[-1], y_ground, 0.0]),
            color=PANEL_STROKE,
            stroke_width=2,
        )
        ground_right = Line(
            np.array([right_nodes[0], y_ground, 0.0]),
            np.array([right_nodes[-1], y_ground, 0.0]),
            color=PANEL_STROKE,
            stroke_width=2,
        )
        group.add(ground_left, ground_right)

        def add_series_section(x_start: float, x_end: float, index: int) -> None:
            segment_width = x_end - x_start
            resistor_start = x_start + segment_width * 0.10
            resistor_end = x_start + segment_width * 0.38
            inductor_start = x_start + segment_width * 0.48
            inductor_end = x_start + segment_width * 0.82
            section_color = BLUE if index % 2 == 0 else CYAN
            left_lead = Line(
                np.array([x_start, y_top, 0.0]),
                np.array([resistor_start, y_top, 0.0]),
                color=section_color,
                stroke_width=2.4,
            )
            resistor_points = []
            for point_index in range(7):
                ratio = float(point_index) / 6.0
                x_value = resistor_start + (resistor_end - resistor_start) * ratio
                y_offset = 0.0
                if point_index not in (0, 6):
                    y_offset = 0.035 if point_index % 2 == 0 else -0.035
                resistor_points.append(np.array([x_value, y_top + y_offset, 0.0]))
            resistor = VMobject(color=ORANGE, stroke_width=1.6)
            resistor.set_points_as_corners(resistor_points)
            middle_lead = Line(
                np.array([resistor_end, y_top, 0.0]),
                np.array([inductor_start, y_top, 0.0]),
                color=section_color,
                stroke_width=2.4,
            )
            inductor = VGroup()
            for coil_index in range(3):
                arc_center_x = inductor_start + (coil_index + 0.5) * (inductor_end - inductor_start) / 3.0
                arc = Arc(
                    radius=0.04,
                    start_angle=PI,
                    angle=-PI,
                    color=CYAN,
                    stroke_width=1.6,
                )
                arc.move_to(np.array([arc_center_x, y_top, 0.0]))
                inductor.add(arc)
            right_lead = Line(
                np.array([inductor_end, y_top, 0.0]),
                np.array([x_end, y_top, 0.0]),
                color=section_color,
                stroke_width=2.4,
            )
            group.add(left_lead, resistor, middle_lead, inductor, right_lead)

        visible_sections = list(range(left_count))
        right_start_index = sections - right_count
        for offset in range(right_count):
            visible_sections.append(right_start_index + offset)

        for local_index in range(left_count):
            add_series_section(
                float(left_nodes[local_index]),
                float(left_nodes[local_index + 1]),
                visible_sections[local_index],
            )
        for local_index in range(right_count):
            add_series_section(
                float(right_nodes[local_index]),
                float(right_nodes[local_index + 1]),
                visible_sections[left_count + local_index],
            )

        ellipsis_top = Text("...", font_size=28, color=MUTED)
        ellipsis_top.move_to(np.array([0.0, y_top + 0.02, 0.0]))
        ellipsis_ground = Text("...", font_size=22, color=PANEL_STROKE)
        ellipsis_ground.move_to(np.array([0.0, y_ground + 0.03, 0.0]))
        group.add(ellipsis_top, ellipsis_ground)

        for index, x_value in enumerate(x_values):
            is_terminal = index == 0 or index == len(x_values) - 1
            dot_radius = 0.035 if not is_terminal else 0.055
            group.add(Dot(np.array([x_value, y_top, 0.0]), radius=dot_radius, color=TEXT))
            if not is_terminal:
                plate_y = -0.12
                upper_plate_y = plate_y + 0.04
                lower_plate_y = plate_y - 0.04
                wire = Line(
                    np.array([x_value, y_top, 0.0]),
                    np.array([x_value, upper_plate_y, 0.0]),
                    color=MUTED,
                    stroke_width=1.4,
                )
                plate_a = Line(
                    np.array([x_value - 0.055, upper_plate_y, 0.0]),
                    np.array([x_value + 0.055, upper_plate_y, 0.0]),
                    color=YELLOW,
                    stroke_width=1.8,
                )
                plate_b = Line(
                    np.array([x_value - 0.055, lower_plate_y, 0.0]),
                    np.array([x_value + 0.055, lower_plate_y, 0.0]),
                    color=YELLOW,
                    stroke_width=1.8,
                )
                down = Line(
                    np.array([x_value, lower_plate_y, 0.0]),
                    np.array([x_value, y_ground, 0.0]),
                    color=MUTED,
                    stroke_width=1.2,
                )
                group.add(wire, plate_a, plate_b, down)
        return group

    def tikz_ladder(self, sections: int = 20, termination: str = "open") -> ImageMobject:
        termination_key = termination.lower()
        image_path = LADDER_TIKZ_IMAGE_PATH
        if termination_key == "grounded":
            image_path = GROUNDED_LADDER_TIKZ_IMAGE_PATH
        if not image_path.exists():
            raise FileNotFoundError(
                f"Missing TikZ-rendered ladder circuit image: {image_path}"
            )
        return ImageMobject(str(image_path))

    def mini_pi_section(self) -> VGroup:
        top = Line(LEFT * 1.45, RIGHT * 1.45, color=BLUE, stroke_width=3)
        resistor = self._zigzag(center=LEFT * 0.72, color=ORANGE)
        inductor = self._small_inductor(center=RIGHT * 0.08, color=CYAN)
        caps = VGroup(
            self._capacitor(LEFT * 1.1 + DOWN * 0.72),
            self._capacitor(RIGHT * 1.1 + DOWN * 0.72),
        )
        labels = VGroup(
            Text("Pi section", font_size=18, color=TEXT, weight=BOLD).next_to(top, UP, buff=0.24),
            Text("R, L in series", font_size=12, color=MUTED).next_to(top, DOWN, buff=0.92),
            Text("C/2 at each end", font_size=12, color=YELLOW).next_to(caps, DOWN, buff=0.12),
        )
        return VGroup(top, resistor, inductor, caps, labels)

    def mini_t_section(self) -> VGroup:
        top_left = Line(LEFT * 1.45, LEFT * 0.12, color=BLUE, stroke_width=3)
        top_right = Line(RIGHT * 0.12, RIGHT * 1.45, color=BLUE, stroke_width=3)
        left_inductor = self._small_inductor(center=LEFT * 0.72, color=CYAN)
        right_inductor = self._small_inductor(center=RIGHT * 0.72, color=CYAN)
        cap = self._capacitor(DOWN * 0.72)
        labels = VGroup(
            Text("T section", font_size=18, color=TEXT, weight=BOLD).next_to(top_left, UP, buff=0.24),
            Text("L/2 - C - L/2", font_size=12, color=MUTED).next_to(cap, DOWN, buff=0.12),
        )
        return VGroup(top_left, top_right, left_inductor, right_inductor, cap, labels)

    def _zigzag(self, center: np.ndarray, color: str) -> VMobject:
        points = []
        x0 = center[0] - 0.34
        for index in range(7):
            x_value = x0 + index * 0.11
            y_value = center[1] + (0.09 if index % 2 == 0 else -0.09)
            if index in (0, 6):
                y_value = center[1]
            points.append(np.array([x_value, y_value, 0.0]))
        return VMobject(color=color, stroke_width=3).set_points_as_corners(points)

    def _small_inductor(self, center: np.ndarray, color: str) -> VGroup:
        group = VGroup()
        for index in range(4):
            x_shift = -0.27 + index * 0.18
            arc = Arc(
                radius=0.105,
                start_angle=PI,
                angle=-PI,
                color=color,
                stroke_width=3,
            )
            arc.move_to(center + RIGHT * x_shift)
            group.add(arc)
        return group

    def _capacitor(self, center: np.ndarray) -> VGroup:
        wire_top = Line(center + UP * 0.58, center + UP * 0.17, color=MUTED, stroke_width=1.8)
        plate_a = Line(center + LEFT * 0.18 + UP * 0.08, center + RIGHT * 0.18 + UP * 0.08, color=YELLOW, stroke_width=2.2)
        plate_b = Line(center + LEFT * 0.18 + DOWN * 0.08, center + RIGHT * 0.18 + DOWN * 0.08, color=YELLOW, stroke_width=2.2)
        wire_bottom = Line(center + DOWN * 0.17, center + DOWN * 0.58, color=MUTED, stroke_width=1.8)
        ground = Line(center + LEFT * 0.24 + DOWN * 0.58, center + RIGHT * 0.24 + DOWN * 0.58, color=MUTED, stroke_width=1.6)
        return VGroup(wire_top, plate_a, plate_b, wire_bottom, ground)

    def line_graph(self, axes: Axes, x_values: np.ndarray, y_values: np.ndarray, color: str, width: float = 3.0) -> VMobject:
        points = [
            axes.c2p(float(x_value), float(y_value))
            for x_value, y_value in zip(x_values, y_values)
        ]
        graph = VMobject(color=color, stroke_width=width)
        graph.set_points_smoothly(points)
        return graph


class SurgePresentation(Scene):
    """Single professional lesson scene built from the project data."""

    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.factory = VisualFactory()
        self.data = ProjectDataLoader().load()
        self._base_cfg = None
        self._dist_cache = None

        self.opening_scene()
        self.source_scene()
        self.model_scene(termination="grounded")
        self.initial_distribution_scene()
        self.grounded_return_scene(clear_after=False)

    @staticmethod
    def time_window_end_us(data: NodeVoltageData, requested_end_us: float) -> float:
        data_end_us = float(np.max(data.time_s) * 1e6)
        return min(requested_end_us, data_end_us)

    @staticmethod
    def sample_time_indices(time_us: np.ndarray, end_us: float, count: int) -> np.ndarray:
        valid_indices = np.flatnonzero(time_us <= end_us)
        if len(valid_indices) == 0:
            return np.array([0], dtype=int)
        if len(valid_indices) <= count:
            return valid_indices
        sampled_positions = np.linspace(0, len(valid_indices) - 1, count).astype(int)
        return valid_indices[sampled_positions]

    @staticmethod
    def segment_voltage_percentages(
        positions: np.ndarray,
        voltages: np.ndarray,
        segment_count: int,
    ) -> np.ndarray:
        sample_positions = np.linspace(
            float(np.min(positions)),
            float(np.max(positions)),
            segment_count + 1,
        )
        sample_voltages = np.interp(sample_positions, positions, voltages)
        voltage_drops = np.abs(np.diff(sample_voltages))
        total_drop = float(np.sum(voltage_drops))
        if total_drop <= PERCENT_TOTAL_EPSILON:
            return np.zeros(segment_count, dtype=float)
        return voltage_drops * 100.0 / total_drop

    @staticmethod
    def segment_local_percentages(
        positions: np.ndarray,
        voltages: np.ndarray,
        segment_count: int,
    ) -> np.ndarray:
        segment_shares = SurgePresentation.segment_voltage_percentages(
            positions,
            voltages,
            segment_count,
        )
        return segment_shares * float(segment_count)

    def make_local_percentage_row(
        self,
        axes: Axes,
        positions: np.ndarray,
        voltages: np.ndarray,
        y_limit: float,
        title_text: str,
    ) -> VGroup:
        local_percentages = self.segment_local_percentages(
            positions,
            voltages,
            PERCENT_SEGMENT_COUNT,
        )
        cells = VGroup()
        for index, percentage in enumerate(local_percentages):
            center_position = (float(index) + 0.5) * 100.0 / float(PERCENT_SEGMENT_COUNT)
            cell_center = axes.c2p(center_position, -y_limit) + DOWN * 0.58
            if percentage >= 160.0:
                cell_color = RED
            elif percentage >= 100.0:
                cell_color = ORANGE
            else:
                cell_color = BLUE
            cell = Rectangle(
                width=0.54,
                height=0.28,
                stroke_color=cell_color,
                stroke_width=0.8,
                fill_color=cell_color,
                fill_opacity=0.24,
            )
            cell.move_to(cell_center)
            label_font_size = 8
            if percentage >= 1000.0:
                label_font_size = 6
            elif percentage >= 100.0:
                label_font_size = 7
            label = Text(f"{percentage:.0f}%", font_size=label_font_size, color=TEXT)
            label.move_to(cell_center)
            cells.add(VGroup(cell, label))

        if "grounded" in title_text:
            title = MathTex(
                r"\mathrm{grounded\ local}\ \Delta V_k\ (\%)",
                font_size=18,
                color=MUTED,
            )
        elif "open" in title_text:
            title = MathTex(
                r"\mathrm{open\ local}\ \Delta V_k\ (\%)",
                font_size=18,
                color=MUTED,
            )
        else:
            title = Text(title_text, font_size=13, color=MUTED)
        reference_label = MathTex(
            r"\mathrm{local\ avg}=100\%",
            font_size=17,
            color=GREEN,
        )
        title_group = VGroup(title, reference_label).arrange(RIGHT, buff=0.25)
        title_group.next_to(cells, UP, buff=0.08)
        return VGroup(title_group, cells)

    def make_dynamic_local_percentage_row(
        self,
        axes: Axes,
        positions: np.ndarray,
        voltage_profile_getter,
        y_limit: float,
        title_text: str,
    ) -> VGroup:
        bars = VGroup()
        labels = VGroup()
        bar_bases: list[np.ndarray] = []
        for index in range(PERCENT_SEGMENT_COUNT):
            center_position = (float(index) + 0.5) * 100.0 / float(PERCENT_SEGMENT_COUNT)
            bar_base = axes.c2p(center_position, -y_limit) + DOWN * 0.88
            bar_bases.append(bar_base)
            bar = Rectangle(
                width=0.46,
                height=0.04,
                stroke_color=BLUE,
                stroke_width=0.8,
                fill_color=BLUE,
                fill_opacity=0.62,
            )
            bar.move_to(bar_base + UP * 0.02)
            label = DecimalNumber(
                0,
                num_decimal_places=0,
                font_size=8,
                color=TEXT,
            )
            label.move_to(bar.get_top() + UP * 0.05)
            bars.add(bar)
            labels.add(label)

        if "grounded" in title_text:
            title = MathTex(
                r"\mathrm{grounded\ local}\ \Delta V_k\ (\%)",
                font_size=18,
                color=MUTED,
            )
        elif "open" in title_text:
            title = MathTex(
                r"\mathrm{open\ local}\ \Delta V_k\ (\%)",
                font_size=18,
                color=MUTED,
            )
        else:
            title = Text(title_text, font_size=13, color=MUTED)
        reference_label = MathTex(
            r"\mathrm{local\ avg}=100\%",
            font_size=17,
            color=GREEN,
        )
        title_group = VGroup(title, reference_label).arrange(RIGHT, buff=0.25)
        title_group.next_to(bars, DOWN, buff=0.06)
        row = VGroup(title_group, bars, labels)
        blue_color = ManimColor(BLUE)
        orange_color = ManimColor(ORANGE)
        red_color = ManimColor(RED)

        def update_row(row_group: VGroup) -> VGroup:
            y_values = voltage_profile_getter()
            local_percentages = self.segment_local_percentages(
                positions,
                y_values,
                PERCENT_SEGMENT_COUNT,
            )
            for bar_index in range(PERCENT_SEGMENT_COUNT):
                percentage = float(local_percentages[bar_index])
                normalized = min(max(percentage / LOCAL_BAR_REFERENCE_PERCENT, 0.0), 1.0)
                if normalized <= 0.5:
                    bar_color = interpolate_color(blue_color, orange_color, normalized / 0.5)
                else:
                    bar_color = interpolate_color(orange_color, red_color, (normalized - 0.5) / 0.5)
                bar_base = bar_bases[bar_index]
                bar_height = max(0.035, LOCAL_BAR_MAX_HEIGHT * normalized)
                bars[bar_index].stretch_to_fit_height(bar_height)
                bars[bar_index].move_to(bar_base + UP * (bar_height / 2.0))
                bars[bar_index].set_stroke(bar_color, width=0.8)
                bars[bar_index].set_fill(bar_color, opacity=0.70)
                labels[bar_index].set_value(int(round(percentage)))
                labels[bar_index].set_height(0.115)
                if labels[bar_index].width > 0.44:
                    labels[bar_index].set_width(0.44)
                if bar_height >= 0.28:
                    labels[bar_index].move_to(bars[bar_index].get_center())
                else:
                    labels[bar_index].move_to(bars[bar_index].get_top() + UP * 0.08)
            return row_group

        update_row(row)
        row.add_updater(update_row)
        return row

    def opening_scene(self) -> None:
        title = Text("Surge Propagation", font_size=44, color=TEXT, weight=BOLD)
        subtitle = Text("in a Distributed Coil", font_size=30, color=CYAN)
        coil = self.factory.coil(width=6.2, turns=14).shift(DOWN * 0.25)
        pulse = self.factory.surge_arrow().next_to(coil, LEFT, buff=0.15)
        footer = Text("Python time-domain model + ATP/EMTP validation", font_size=18, color=MUTED)
        footer.to_edge(DOWN, buff=0.55)
        title_group = VGroup(title, subtitle).arrange(DOWN, buff=0.12).to_edge(UP, buff=0.85)

        dot = Dot(color=ORANGE, radius=0.08).move_to(pulse[0].get_start())
        self.play(FadeIn(title_group, shift=DOWN * 0.25), run_time=1.2)
        self.play(FadeIn(coil), GrowArrow(pulse[0]), FadeIn(pulse[1]), run_time=1.3)
        self.play(MoveAlongPath(dot, coil[1]), FadeIn(footer), run_time=2.0, rate_func=linear)
        self.play(FadeOut(dot), Indicate(coil, color=CYAN), run_time=1.0)
        self.wait(0.3)
        self.clear()

    def problem_scene(self) -> None:
        heading = self.factory.heading("Physical Problem", "A fast impulse does not see the coil as one lumped inductor")
        coil = self.factory.coil(width=5.4, turns=12).shift(LEFT * 2.15 + DOWN * 0.25)
        source_panel = self.factory.panel(3.8, 2.2).shift(RIGHT * 3.0 + DOWN * 0.1)
        source_title = Text("Applied impulse", font_size=19, color=TEXT, weight=BOLD)
        source_title.move_to(source_panel.get_top() + DOWN * 0.36)
        lines = VGroup(
            Text("Peak: 1000 V", font_size=17, color=ORANGE),
            Text("Front: 1.2 us", font_size=17, color=CYAN),
            Text("Tail: 50 us", font_size=17, color=CYAN),
            Text("Termination: open circuit", font_size=16, color=MUTED),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        lines.move_to(source_panel.get_center() + DOWN * 0.15)
        arrow = Arrow(LEFT * 5.7 + DOWN * 0.25, LEFT * 3.25 + DOWN * 0.25, color=ORANGE, buff=0.0, stroke_width=6)
        wave_dots = VGroup(*[Dot(radius=0.045, color=ORANGE) for _ in range(6)])
        for index, dot in enumerate(wave_dots):
            dot.move_to(arrow.get_start() + RIGHT * (index * 0.22))

        note = Text("Voltage becomes spatially distributed along the winding.", font_size=18, color=TEXT)
        note.to_edge(DOWN, buff=0.58)

        self.play(FadeIn(heading), FadeIn(source_panel), FadeIn(source_title), FadeIn(lines), run_time=1.0)
        self.play(GrowArrow(arrow), FadeIn(coil), run_time=1.1)
        self.play(
            *[dot.animate.shift(RIGHT * 2.55) for dot in wave_dots],
            FadeIn(note, shift=UP * 0.2),
            run_time=1.8,
            rate_func=linear,
        )
        self.play(Indicate(coil, color=CYAN), run_time=0.8)
        self.wait(0.3)
        self.clear()

    def model_scene(self, termination: str = "open") -> None:
        cfg = self.data.config
        sections = int(cfg["n_sections"])
        termination_key = termination.lower()
        grounded_case = termination_key == "grounded"
        title = "Shorted-End Circuit" if grounded_case else "Open-End Circuit"
        subtitle = (
            "Input source, shorted far end"
            if grounded_case
            else "Input source, open far end"
        )
        heading = self.factory.heading(
            title,
            subtitle,
        )
        ladder = self.factory.tikz_ladder(sections=sections, termination=termination_key)
        ladder.set_width(12.25)
        ladder.shift(UP * 0.7)
        legend = VGroup(
            MathTex("R", font_size=24, color=ORANGE),
            Text("series resistance", font_size=13, color=MUTED),
            MathTex("L", font_size=24, color=CYAN),
            Text("series inductance", font_size=13, color=MUTED),
            MathTex("C", font_size=24, color=YELLOW),
            Text("shunt capacitance", font_size=13, color=MUTED),
        ).arrange(RIGHT, buff=0.16)
        legend.next_to(ladder, DOWN, buff=0.18)

        per_section = VGroup(
            MathTex(
                rf"L_{{\mathrm{{total}}}} = {float(cfg['L_total']) * 1e3:.1f}\,\mathrm{{mH}}",
                font_size=26,
                color=CYAN,
            ),
            MathTex(
                rf"R_{{\mathrm{{total}}}} = {float(cfg['R_total']):.1f}\,\Omega",
                font_size=26,
                color=ORANGE,
            ),
            MathTex(
                rf"C_{{\mathrm{{total}}}} = {float(cfg['C_total']) * 1e9:.1f}\,\mathrm{{nF}}",
                font_size=26,
                color=YELLOW,
            ),
            Text("State-space ODE solved with scipy", font_size=16, color=MUTED),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        per_section.to_edge(DOWN, buff=0.45).shift(LEFT * 3.3)

        source_statement = VGroup(
            Text("source:", font_size=18, color=TEXT),
            MathTex("V_s(t)", font_size=28, color=ORANGE),
            Text("input", font_size=18, color=TEXT),
            MathTex(r"\rightarrow", font_size=24, color=MUTED),
            Text("reference", font_size=18, color=TEXT),
        ).arrange(RIGHT, buff=0.16)
        local_voltage_statement = VGroup(
            Text("local", font_size=18, color=YELLOW),
            MathTex(r"\Delta V_k", font_size=28, color=YELLOW),
            Text("is measured section by section", font_size=18, color=YELLOW),
        ).arrange(RIGHT, buff=0.10)
        concept_note = VGroup(
            source_statement,
            Text(
                "far terminal: shorted to reference"
                if grounded_case
                else "far terminal: open circuit",
                font_size=18,
                color=GREEN if grounded_case else RED,
            ),
            local_voltage_statement,
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        concept_note.to_edge(DOWN, buff=0.47).shift(RIGHT * 2.65)

        self.play(FadeIn(heading), run_time=0.7)
        self.play(FadeIn(ladder, shift=UP * 0.08), run_time=1.2)
        self.play(FadeIn(legend), FadeIn(per_section, shift=RIGHT * 0.2), run_time=0.8)
        self.play(FadeIn(concept_note, shift=UP * 0.15), run_time=1.1)
        self.play(Circumscribe(ladder, color=CYAN, time_width=0.6), run_time=1.1)
        self.wait(0.3)
        self.clear()

    # ------------------------------------------------------------------
    # Initial (t=0+) capacitive distribution
    # ------------------------------------------------------------------

    def _base_config_obj(self) -> SimulationConfig:
        """Project base config as a validated dataclass (cached)."""
        if getattr(self, "_base_cfg", None) is None:
            self._base_cfg = SimulationConfig(**self.data.config)
        return self._base_cfg

    def _initial_distribution(
        self,
        alpha: float,
        termination: str = "grounded",
        n_sections: int = 80,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Real t=0+ capacitive distribution straight from the model.

        alpha = sqrt(C_total / C_series_total) is the winding distribution
        factor, so C_series_total = C_total / alpha^2.  Returns
        (position %, voltage %) over the Pi nodes, input node at 100 %.
        """
        base = self._base_config_obj()
        c_series = float(base.C_total) / (alpha * alpha)
        case = base.copy_with(
            n_sections=n_sections,
            C_series_total=c_series,
            termination=termination,
            model_type="pi",
        )
        coil = DistributedCoil(case)
        positions, voltages = coil.initial_voltage_distribution(v_input=1.0)
        return positions * 100.0, voltages * 100.0

    def _cached_distribution(
        self, alpha: float, n_sections: int = 80
    ) -> tuple[np.ndarray, np.ndarray]:
        """One model solve per (alpha, N); reused by the curve and readouts
        within the same animation frame."""
        cache = getattr(self, "_dist_cache", None)
        if cache is not None and cache[0] == alpha and cache[3] == n_sections:
            return cache[1], cache[2]
        xs, vs = self._initial_distribution(alpha, "grounded", n_sections)
        self._dist_cache = (alpha, xs, vs, n_sections)
        return xs, vs

    def initial_distribution_scene(self) -> None:
        heading = self.factory.heading(
            "Initial Voltage Distribution (t = 0+)",
            "At the surge front the inductors block current, so the coil "
            "splits the voltage like a capacitive divider",
        )

        axes = Axes(
            x_range=[0, 100, 20],
            y_range=[0, 100, 20],
            x_length=10.6,
            y_length=4.0,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).shift(DOWN * 0.35)
        x_label = MathTex(r"x_{\mathrm{coil}}\;(\%)", font_size=22, color=MUTED)
        x_label.next_to(axes.x_axis.get_end(), DOWN, buff=0.2)
        y_label = MathTex(r"v/V_0\;(\%)", font_size=22, color=MUTED)
        y_label.rotate(PI / 2).next_to(axes.y_axis, LEFT, buff=0.2)
        labels = VGroup(x_label, y_label)

        # uniform (ideal) reference: a straight 100 % -> 0 % line
        uniform = DashedVMobject(
            self.factory.line_graph(
                axes, np.array([0.0, 100.0]), np.array([100.0, 0.0]),
                MUTED, width=2.5,
            ),
            num_dashes=34,
        )
        uniform_label = Text("uniform (ideal split)", font_size=15, color=MUTED)
        uniform_label.move_to(axes.c2p(74, 46))

        # entrance band: the first 10 % of the winding
        entrance_frac = 10.0
        x0 = axes.c2p(0.0, 0.0)
        x1 = axes.c2p(entrance_frac, 0.0)
        y_top = axes.c2p(0.0, 100.0)
        band = Rectangle(
            width=float(x1[0] - x0[0]),
            height=float(y_top[1] - x0[1]),
            stroke_width=0,
            fill_color=RED,
            fill_opacity=0.10,
        )
        band.move_to((x0 + axes.c2p(entrance_frac, 100.0)) / 2.0)
        band_label = Text("entrance (first 10%)", font_size=14, color=RED)
        band_label.next_to(axes.c2p(5.0, 0.0), DOWN, buff=0.3)

        # input / grounded-end markers
        input_dot = Dot(axes.c2p(0.0, 100.0), radius=0.06, color=ORANGE)
        ground_dot = Dot(axes.c2p(100.0, 0.0), radius=0.06, color=GREEN)
        ground_text = Text("grounded end", font_size=14, color=GREEN)
        ground_text.next_to(ground_dot, UP, buff=0.12)

        alpha_tracker = ValueTracker(0.6)
        n_curve = 80

        def make_curve() -> VMobject:
            xs, vs = self._cached_distribution(alpha_tracker.get_value(), n_curve)
            return self.factory.line_graph(axes, xs, vs, CYAN, width=4.5)
        curve = always_redraw(make_curve)

        # readouts (kept in the always-free upper-right corner of the plot)
        alpha_label = MathTex(r"\alpha=\sqrt{C_g/C_s}=", font_size=26, color=CYAN)
        alpha_value = DecimalNumber(0.6, num_decimal_places=1, font_size=26,
                                    color=CYAN)
        alpha_value.next_to(alpha_label, RIGHT, buff=0.12)
        alpha_value.add_updater(lambda m: m.set_value(alpha_tracker.get_value()))
        alpha_row = VGroup(alpha_label, alpha_value)

        share_label = Text("first 10% holds", font_size=20, color=RED)
        share_value = DecimalNumber(11, num_decimal_places=0, unit=r"\%",
                                    font_size=26, color=RED)
        share_value.next_to(share_label, RIGHT, buff=0.12)

        def update_share(m: DecimalNumber) -> None:
            xs, vs = self._cached_distribution(alpha_tracker.get_value(), n_curve)
            v10 = float(np.interp(entrance_frac, xs, vs))
            m.set_value(100.0 - v10)
        share_value.add_updater(update_share)
        share_row = VGroup(share_label, share_value)

        readout = VGroup(alpha_row, share_row).arrange(
            DOWN, aligned_edge=LEFT, buff=0.26)
        readout.move_to(axes.c2p(70, 84), aligned_edge=LEFT)

        footer = Text(
            "Series (turn-to-turn) capacitance Cs sets alpha; larger alpha "
            "crowds the voltage onto the entrance turns.",
            font_size=17, color=TEXT,
        )
        footer.to_edge(DOWN, buff=0.32)

        self.play(FadeIn(heading), Create(axes), FadeIn(labels), run_time=1.0)
        self.play(
            Create(uniform), FadeIn(uniform_label),
            FadeIn(input_dot),
            FadeIn(ground_dot), FadeIn(ground_text),
            run_time=1.0,
        )
        self.play(FadeIn(band), FadeIn(band_label), run_time=0.6)
        self.play(FadeIn(curve), FadeIn(readout), run_time=0.8)
        self.play(
            alpha_tracker.animate.set_value(10.0),
            run_time=5.5,
            rate_func=smooth,
        )
        self.play(
            FadeIn(footer, shift=UP * 0.15),
            Indicate(band, color=RED, scale_factor=1.04),
            run_time=1.0,
        )
        # settle on the alpha carried into the time-domain animation (scene 5)
        self.play(
            alpha_tracker.animate.set_value(TIME_DOMAIN_ALPHA),
            run_time=1.6,
            rate_func=smooth,
        )
        alpha_value.clear_updaters()
        share_value.clear_updaters()
        carry = VGroup(
            MathTex(rf"\alpha = {TIME_DOMAIN_ALPHA:.0f}", font_size=26, color=CYAN),
            Text("followed in time next", font_size=16, color=CYAN),
        ).arrange(RIGHT, buff=0.2)
        carry.next_to(readout, DOWN, buff=0.4).align_to(readout, LEFT)
        self.play(FadeIn(carry, shift=UP * 0.1), run_time=0.8)
        self.play(Indicate(carry, color=CYAN), run_time=0.7)
        self.wait(0.5)
        self.clear()

    def source_scene(self) -> None:
        heading = self.factory.heading(
            "Impulse Source",
            "1.2/50 us waveform used as the input voltage source",
        )
        cfg = self.data.config
        source = ImpulseSource(
            source_type=str(cfg["source_type"]),
            amplitude=float(cfg["V_amplitude"]),
            t_front=float(cfg["t_front"]),
            t_tail=float(cfg["t_tail"]),
        )
        display_end_us = STATIC_TIME_WINDOW_US
        time_us = np.linspace(0.0, display_end_us, 900)
        source_v = source.evaluate_array(time_us * 1e-6)
        source_percent = source_v * 100.0 / float(np.max(np.abs(source_v)))
        sample = self.sample_time_indices(time_us, display_end_us, 620)
        panel = self.factory.panel(12.45, 4.95)
        panel.move_to(DOWN * 0.18)
        axes = Axes(
            x_range=[0, display_end_us, 25],
            y_range=[0, 110, 25],
            x_length=10.75,
            y_length=3.15,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        )
        axes.move_to(panel.get_center() + UP * 0.28)
        x_label = MathTex(r"t\;(\mu\mathrm{s})", font_size=24, color=MUTED)
        x_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.12)
        y_label = MathTex(
            r"v_s/V_{\mathrm{peak}}\;(\%)",
            font_size=24,
            color=MUTED,
        )
        y_label.move_to(axes.c2p(11.0, 108.0))
        labels = VGroup(x_label, y_label)
        graph = self.factory.line_graph(axes, time_us[sample], source_percent[sample], ORANGE, width=3.6)
        graph_glow = graph.copy()
        graph_glow.set_stroke(ORANGE, width=8.0, opacity=0.18)
        graph.set_z_index(2)
        graph_glow.set_z_index(1)
        peak_time_us = float(source.peak_time * 1e6)
        peak_point = axes.c2p(peak_time_us, 100.0)
        peak_dot = Dot(peak_point, color=YELLOW, radius=0.07)
        front_x = float(cfg["t_front"]) * 1e6
        tail_x = float(cfg["t_tail"]) * 1e6
        front_y = float(np.interp(front_x, time_us, source_percent))
        tail_y = float(np.interp(tail_x, time_us, source_percent))
        front_dot = Dot(axes.c2p(front_x, front_y), color=CYAN, radius=0.06)
        tail_dot = Dot(axes.c2p(tail_x, tail_y), color=BLUE, radius=0.06)
        peak_dot.set_z_index(5)
        front_dot.set_z_index(5)
        tail_dot.set_z_index(5)
        peak_line = DashedLine(
            axes.c2p(0.0, 100.0),
            axes.c2p(display_end_us, 100.0),
            color=YELLOW,
            stroke_width=1.6,
            dash_length=0.14,
        )
        half_line = DashedLine(
            axes.c2p(0.0, 50.0),
            axes.c2p(tail_x, 50.0),
            color=BLUE,
            stroke_width=1.6,
            dash_length=0.14,
        )
        front_line = DashedLine(
            axes.c2p(front_x, 0.0),
            axes.c2p(front_x, front_y),
            color=CYAN,
            stroke_width=2.0,
        )
        tail_line = DashedLine(
            axes.c2p(tail_x, 0.0),
            axes.c2p(tail_x, tail_y),
            color=BLUE,
            stroke_width=2.0,
        )
        guide_lines = VGroup(peak_line, half_line, front_line, tail_line)
        guide_lines.set_z_index(0)

        def callout(title: str, detail_tex: str, color: str, width: float = 2.05) -> VGroup:
            box = RoundedRectangle(
                width=width,
                height=0.68,
                corner_radius=0.08,
                fill_color=BACKGROUND,
                fill_opacity=0.86,
                stroke_color=color,
                stroke_width=1.1,
            )
            title_mob = Text(title, font_size=13, color=color, weight=BOLD)
            detail_mob = MathTex(detail_tex, font_size=21, color=TEXT)
            text_group = VGroup(title_mob, detail_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.01)
            text_group.move_to(box.get_center())
            group = VGroup(box, text_group)
            group.set_z_index(6)
            return group

        peak_label = callout("Peak", r"100\%\ \mathrm{reference}", YELLOW, width=2.10)
        peak_label.move_to(axes.c2p(27.0, 93.0))
        front_label = callout("Front time", r"T_1 = 1.2\,\mu\mathrm{s}", CYAN, width=2.25)
        front_label.move_to(axes.c2p(20.0, 32.0))
        tail_label = callout("Tail time", r"T_2 = 50\,\mu\mathrm{s}", BLUE, width=2.15)
        tail_label.move_to(axes.c2p(73.0, 72.0))

        def note_card(title: str, detail: str, color: str) -> VGroup:
            box = RoundedRectangle(
                width=3.55,
                height=0.58,
                corner_radius=0.07,
                fill_color=BACKGROUND,
                fill_opacity=0.48,
                stroke_color=PANEL_STROKE,
                stroke_width=0.9,
            )
            title_mob = Text(title, font_size=12, color=color, weight=BOLD)
            detail_mob = Text(detail, font_size=11, color=MUTED)
            text_group = VGroup(title_mob, detail_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.02)
            text_group.move_to(box.get_center())
            return VGroup(box, text_group)

        definition = VGroup(
            note_card("Fast front", "First sections charge first.", CYAN),
            note_card("Tail", "Voltage remains during redistribution.", BLUE),
        ).arrange(RIGHT, buff=0.24)
        definition.next_to(axes, DOWN, buff=0.36).align_to(axes, LEFT)
        source_badge = VGroup(
            RoundedRectangle(
                width=1.92,
                height=0.62,
                corner_radius=0.08,
                fill_color=ORANGE,
                fill_opacity=0.16,
                stroke_color=ORANGE,
                stroke_width=1.1,
            ),
            MathTex("V_s(t)", font_size=34, color=ORANGE),
        )
        source_badge[1].move_to(source_badge[0].get_center())
        source_badge.next_to(definition, RIGHT, buff=0.42)
        source_badge.align_to(definition, DOWN)
        notable_points = VGroup(
            guide_lines,
            peak_dot,
            front_dot,
            tail_dot,
            peak_label,
            front_label,
            tail_label,
        )

        self.play(FadeIn(heading), FadeIn(panel), Create(axes), FadeIn(labels), run_time=1.0)
        self.play(Create(graph_glow), Create(graph), run_time=1.7)
        self.play(
            FadeIn(notable_points),
            run_time=1.0,
        )
        self.play(FadeIn(definition, shift=UP * 0.1), FadeIn(source_badge, shift=LEFT * 0.1), run_time=0.7)
        self.wait(1.0)
        self.clear()

    def travelling_wave_scene(self) -> None:
        heading = self.factory.heading(
            "Open-End Travelling Wave",
            "Local dV percentages: 100% means one average segment drop",
        )
        data = self.data.pi_nodes
        time_us = data.time_s * 1e6
        animation_end_us = self.time_window_end_us(data, ANIMATION_TIME_WINDOW_US)
        y_limit = max(2250.0, float(np.ceil(np.max(np.abs(data.voltages)) / 500.0) * 500.0))
        y_step = 500.0 if y_limit <= 3000.0 else 1000.0
        axes = Axes(
            x_range=[0, 100, 20],
            y_range=[-y_limit, y_limit, y_step],
            x_length=WIDE_GRAPH_X_LENGTH,
            y_length=3.55,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).shift(UP * 0.05)
        x_label = MathTex(r"x_{\mathrm{coil}}\;(\%)", font_size=22, color=MUTED)
        x_label.next_to(axes.x_axis.get_end(), RIGHT, buff=0.14)
        y_label = MathTex(r"v\;(\mathrm{V})", font_size=22, color=MUTED)
        y_label.move_to(axes.c2p(6.0, y_limit * 0.92))
        labels = VGroup(x_label, y_label)
        tracker = ValueTracker(0.0)

        def current_voltage_profile() -> np.ndarray:
            current_time_s = tracker.get_value() * 1e-6
            values = [
                np.interp(current_time_s, data.time_s, data.voltages[index])
                for index in range(data.voltages.shape[0])
            ]
            return np.asarray(values, dtype=float)

        def make_profile() -> VGroup:
            y_values = current_voltage_profile()
            x_values = data.positions * 100.0
            line = self.factory.line_graph(axes, x_values, y_values, CYAN, width=4.0)
            dots = VGroup(
                *[
                    Dot(
                        axes.c2p(float(x_value), float(y_value)),
                        radius=0.045,
                        color=self.voltage_color(float(y_value)),
                    )
                    for x_value, y_value in zip(x_values, y_values)
                ]
            )
            return VGroup(line, dots)

        profile = always_redraw(make_profile)
        percentage_row = self.make_dynamic_local_percentage_row(
            axes,
            data.positions,
            current_voltage_profile,
            y_limit,
            "open-end local dV (%)",
        )
        time_symbol = MathTex("t =", font_size=28, color=YELLOW)
        time_value = DecimalNumber(
            0,
            num_decimal_places=2,
            font_size=22,
            color=YELLOW,
        )
        time_unit = MathTex(r"\mu\mathrm{s}", font_size=28, color=YELLOW)
        time_label = VGroup(time_symbol, time_value, time_unit).arrange(RIGHT, buff=0.08)
        time_label.to_corner(UR, buff=0.55)

        def update_time_label(label_group: VGroup) -> VGroup:
            time_value.set_value(tracker.get_value())
            label_group.arrange(RIGHT, buff=0.08)
            label_group.to_corner(UR, buff=0.55)
            return label_group

        time_label.add_updater(update_time_label)
        input_arrow = Arrow(
            axes.c2p(0, 1000),
            axes.c2p(15, 1000),
            color=ORANGE,
            stroke_width=5,
            buff=0.0,
        )
        input_text = Text("surge enters", font_size=15, color=ORANGE).next_to(input_arrow, UP, buff=0.08)

        self.play(FadeIn(heading), Create(axes), FadeIn(labels), run_time=1.0)
        self.play(
            FadeIn(profile),
            FadeIn(percentage_row),
            FadeIn(time_label),
            GrowArrow(input_arrow),
            FadeIn(input_text),
            run_time=0.8,
        )
        self.play(
            tracker.animate.set_value(animation_end_us),
            run_time=ANIMATION_PROFILE_RUN_TIME,
            rate_func=linear,
        )
        self.play(Indicate(profile, color=YELLOW), Indicate(percentage_row, color=YELLOW), run_time=0.8)
        self.wait(0.3)
        self.clear()

    def reflection_scene(self) -> None:
        scalars = self.data.pi_scalars
        heading = self.factory.heading("Open-End Reflection", "The reflected wave approximately doubles the output voltage")
        v_in = scalars["V_peak_in_V"]
        v_out = scalars["V_peak_out_V"]
        ratio = scalars["transfer_ratio"]

        coil = self.factory.coil(width=6.0, turns=13).shift(UP * 0.25)
        incoming = Arrow(LEFT * 5.5 + UP * 0.25, LEFT * 3.4 + UP * 0.25, color=ORANGE, buff=0.0, stroke_width=6)
        reflected = Arrow(RIGHT * 3.4 + UP * 0.25, RIGHT * 1.25 + UP * 0.25, color=RED, buff=0.0, stroke_width=6)
        open_marker = VGroup(
            Line(RIGHT * 3.35 + UP * 0.85, RIGHT * 3.35 + DOWN * 0.35, color=RED, stroke_width=4),
            Text("open end", font_size=15, color=RED).next_to(RIGHT * 3.35 + DOWN * 0.35, DOWN, buff=0.08),
        )

        cards = VGroup(
            self.metric_card("Input peak", f"{v_in:.0f} V", ORANGE),
            self.metric_card("Output peak", f"{v_out:.2f} V", RED),
            self.metric_card("Transfer ratio", f"{ratio:.6f}", CYAN),
        ).arrange(RIGHT, buff=0.35)
        cards.to_edge(DOWN, buff=0.55)

        note = Text("Reflection coefficient near +1 at an open terminal", font_size=18, color=TEXT)
        note.next_to(coil, DOWN, buff=0.5)

        self.play(FadeIn(heading), FadeIn(coil), FadeIn(open_marker), run_time=1.0)
        self.play(GrowArrow(incoming), FadeIn(note), run_time=1.0)
        self.play(GrowArrow(reflected), Indicate(open_marker, color=RED), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(card, shift=UP * 0.15) for card in cards], lag_ratio=0.15), run_time=1.2)
        self.wait(0.4)
        self.clear()

    def grounded_return_scene(self, clear_after: bool = True) -> None:
        heading = self.factory.heading(
            "Initial to Final Distribution",
            "Grounded coil: the surge starts crowded at the entrance, then relaxes toward uniform",
        )
        data = self.data.grounded_nodes
        animation_end_us = self.time_window_end_us(data, ANIMATION_TIME_WINDOW_US)
        y_limit = max(1100.0, float(np.ceil(np.max(np.abs(data.voltages)) / 500.0) * 500.0))
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

        def current_voltage_profile() -> np.ndarray:
            current_time_s = tracker.get_value() * 1e-6
            values = [
                np.interp(current_time_s, data.time_s, data.voltages[index])
                for index in range(data.voltages.shape[0])
            ]
            return np.asarray(values, dtype=float)

        def make_profile() -> VGroup:
            y_values = current_voltage_profile()
            x_values = data.positions * 100.0
            line = self.factory.line_graph(axes, x_values, y_values, GREEN, width=4.0)
            dots = VGroup(
                *[
                    Dot(
                        axes.c2p(float(x_value), float(y_value)),
                        radius=0.045,
                        color=self.voltage_color(float(y_value)),
                    )
                    for x_value, y_value in zip(x_values, y_values)
                ]
            )
            return VGroup(line, dots)

        profile = always_redraw(make_profile)

        # reference: the final (uniform) profile the surge relaxes toward,
        # a straight line from the instantaneous input voltage down to the
        # grounded end.  The live profile starts crowded and tends to it.
        def make_uniform_ref() -> VMobject:
            v_in = float(current_voltage_profile()[0])
            ref = self.factory.line_graph(
                axes, np.array([0.0, 100.0]), np.array([v_in, 0.0]),
                MUTED, width=2.0,
            )
            return DashedVMobject(ref, num_dashes=26)
        uniform_ref = always_redraw(make_uniform_ref)
        uniform_ref_label = Text("uniform (final)", font_size=14, color=MUTED)
        uniform_ref_label.move_to(axes.c2p(70.0, y_limit * 0.42))

        percentage_row = self.make_dynamic_local_percentage_row(
            axes,
            data.positions,
            current_voltage_profile,
            y_limit,
            "grounded local dV (%)",
        )
        time_symbol = MathTex("t =", font_size=28, color=YELLOW)
        time_value = DecimalNumber(
            0,
            num_decimal_places=2,
            font_size=22,
            color=YELLOW,
        )
        time_unit = MathTex(r"\mu\mathrm{s}", font_size=28, color=YELLOW)
        time_label = VGroup(time_symbol, time_value, time_unit).arrange(RIGHT, buff=0.08)
        time_label.to_corner(UR, buff=0.55)

        def update_time_label(label_group: VGroup) -> VGroup:
            time_value.set_value(tracker.get_value())
            label_group.arrange(RIGHT, buff=0.08)
            label_group.to_corner(UR, buff=0.55)
            return label_group

        time_label.add_updater(update_time_label)
        ground_dot = Dot(axes.c2p(100.0, 0.0), radius=0.07, color=GREEN)
        ground_label = Text("end tied to reference", font_size=15, color=GREEN)
        ground_label.move_to(axes.c2p(78.0, -y_limit * 0.36))
        ground_leader = Line(
            ground_label.get_right() + RIGHT * 0.08 + UP * 0.02,
            ground_dot.get_center() + LEFT * 0.12,
            color=GREEN,
            stroke_width=2.0,
        )
        ground_marker = VGroup(ground_dot, ground_leader, ground_label)
        source_label = VGroup(
            Text("source input", font_size=15, color=ORANGE),
            MathTex(rf"\alpha = {TIME_DOMAIN_ALPHA:.0f}", font_size=20, color=CYAN),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        source_label.move_to(axes.c2p(13.0, y_limit * 0.72))

        self.play(FadeIn(heading), Create(axes), FadeIn(labels), run_time=1.0)
        self.play(
            FadeIn(uniform_ref),
            FadeIn(uniform_ref_label),
            FadeIn(profile),
            FadeIn(percentage_row),
            FadeIn(time_label),
            FadeIn(ground_marker),
            FadeIn(source_label),
            run_time=0.8,
        )
        self.play(
            tracker.animate.set_value(animation_end_us),
            run_time=getattr(self, "profile_run_time", ANIMATION_PROFILE_RUN_TIME),
            rate_func=linear,
        )
        self.play(
            Circumscribe(ground_marker, color=GREEN),
            Indicate(percentage_row, color=YELLOW),
            run_time=1.1,
        )
        self.wait(0.3)
        if clear_after:
            self.clear()

    def pi_t_scene(self) -> None:
        heading = self.factory.heading("Pi Model vs T Model", "Different section topology, same distributed physics for this case")
        pi = self.data.pi_nodes
        t_model = self.data.t_nodes
        pi_scalars = self.data.pi_scalars
        t_scalars = self.data.t_scalars
        time_pi = pi.time_s * 1e6
        time_t = t_model.time_s * 1e6
        display_end_us = min(
            self.time_window_end_us(pi, STATIC_TIME_WINDOW_US),
            self.time_window_end_us(t_model, STATIC_TIME_WINDOW_US),
        )

        axes = Axes(
            x_range=[0, display_end_us, 5],
            y_range=[0, 2250, 500],
            x_length=11.1,
            y_length=4.1,
            tips=False,
            axis_config={"color": MUTED, "stroke_width": 2},
        ).shift(DOWN * 0.35)
        labels = axes.get_axis_labels(
            Text("time (us)", font_size=15, color=MUTED),
            Text("output voltage (V)", font_size=15, color=MUTED),
        )
        sample_pi = self.sample_time_indices(time_pi, display_end_us, 560)
        sample_t = self.sample_time_indices(time_t, display_end_us, 560)
        graph_pi = self.factory.line_graph(axes, time_pi[sample_pi], pi.voltages[-1, sample_pi], BLUE, width=3.0)
        graph_t = self.factory.line_graph(axes, time_t[sample_t], t_model.voltages[-1, sample_t], ORANGE, width=2.6)
        legend = VGroup(
            self.legend_item(BLUE, f"Pi: peak {pi_scalars['V_peak_out_V']:.4f} V"),
            self.legend_item(ORANGE, f"T: peak {t_scalars['V_peak_out_V']:.4f} V"),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        legend.move_to(RIGHT * 3.55 + UP * 2.05)
        delta = abs(pi_scalars["V_peak_out_V"] - t_scalars["V_peak_out_V"])
        conclusion = Text(f"Peak difference: {delta:.4f} V", font_size=20, color=GREEN, weight=BOLD)
        conclusion.to_edge(DOWN, buff=0.42)

        self.play(FadeIn(heading), Create(axes), FadeIn(labels), run_time=1.0)
        self.play(Create(graph_pi), FadeIn(legend[0]), run_time=1.2)
        self.play(Create(graph_t), FadeIn(legend[1]), run_time=1.2)
        self.play(FadeIn(conclusion, shift=UP * 0.16), Circumscribe(legend, color=GREEN), run_time=1.0)
        self.wait(0.4)
        self.clear()

    def python_atp_scene(self) -> None:
        heading = self.factory.heading("Python vs ATP/EMTP", "Independent solver cross-validation at representative nodes")
        rows = self.data.atp_rows
        table = self.atp_table(rows).shift(DOWN * 0.05)
        worst = max(rows, key=lambda row: abs(float(row["dif_pico_pct"])))
        statement = Text(
            f"Worst peak difference: {abs(float(worst['dif_pico_pct'])):.3f}% at {worst['node']}",
            font_size=21,
            color=GREEN,
            weight=BOLD,
        )
        statement.to_edge(DOWN, buff=0.48)
        badge = VGroup(
            Circle(radius=0.32, color=GREEN, stroke_width=4),
            Text("OK", font_size=18, color=GREEN, weight=BOLD),
        )
        badge.to_corner(UR, buff=0.6)

        self.play(FadeIn(heading), run_time=0.7)
        self.play(FadeIn(table, shift=UP * 0.12), run_time=1.4)
        self.play(FadeIn(statement), FadeIn(badge), run_time=0.9)
        self.play(Circumscribe(statement, color=GREEN), run_time=0.9)
        self.wait(0.4)
        self.clear()

    def limitations_scene(self) -> None:
        heading = self.factory.heading("Engineering Limits", "What this model captures, and what it deliberately leaves out")
        items = [
            ("Linear network", "no saturation or nonlinear insulation effects"),
            ("No turn-to-turn capacitance", "only shunt capacitance to ground is represented"),
            ("Frequency-independent losses", "skin effect and dielectric loss are not modeled"),
            ("Didactic parameters", "replace with measured data for a real coil"),
        ]
        rows = VGroup()
        for title, detail in items:
            marker = Dot(radius=0.07, color=ORANGE)
            title_mob = Text(title, font_size=21, color=TEXT, weight=BOLD)
            detail_mob = Text(detail, font_size=16, color=MUTED)
            text_group = VGroup(title_mob, detail_mob).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
            row = VGroup(marker, text_group).arrange(RIGHT, buff=0.22)
            rows.add(row)
        rows.arrange(DOWN, aligned_edge=LEFT, buff=0.34)
        rows.move_to(ORIGIN + DOWN * 0.15)
        reminder = Text("Useful as an auditable study model, not as a direct product design.", font_size=18, color=CYAN)
        reminder.to_edge(DOWN, buff=0.55)

        self.play(FadeIn(heading), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(row, shift=RIGHT * 0.2) for row in rows], lag_ratio=0.18), run_time=1.8)
        self.play(FadeIn(reminder), run_time=0.8)
        self.wait(0.4)
        self.clear()

    def closing_scene(self) -> None:
        title = Text("Key Takeaways", font_size=36, color=TEXT, weight=BOLD)
        title.to_edge(UP, buff=0.7)
        coil = self.factory.coil(width=4.6, turns=10).to_edge(DOWN, buff=0.8)
        takeaways = VGroup(
            self.takeaway("1", "A surge travels as a spatial wave along the winding."),
            self.takeaway("2", "The boundary condition controls reflection and terminal voltage."),
            self.takeaway("3", "Pi and T discretizations agree for the studied case."),
            self.takeaway("4", "ATP confirms the Python result at key nodes."),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.18)
        takeaways.move_to(UP * 0.15)
        final = Text("Simulation, visualization, and validation stay tied to the same data.", font_size=18, color=CYAN)
        final.next_to(coil, UP, buff=0.45)

        self.play(FadeIn(title), run_time=0.7)
        self.play(LaggedStart(*[FadeIn(item, shift=UP * 0.12) for item in takeaways], lag_ratio=0.16), run_time=1.8)
        self.play(FadeIn(coil), FadeIn(final), run_time=1.2)
        self.wait(1.0)

    @staticmethod
    def voltage_color(voltage: float) -> str:
        magnitude = abs(voltage)
        if magnitude >= 1800.0:
            return RED
        if magnitude >= 1200.0:
            return ORANGE
        if magnitude >= 600.0:
            return CYAN
        return BLUE

    def metric_card(self, label: str, value: str, color: str) -> VGroup:
        panel = self.factory.panel(3.35, 1.35)
        label_mob = Text(label, font_size=15, color=MUTED)
        value_mob = Text(value, font_size=25, color=color, weight=BOLD)
        content = VGroup(label_mob, value_mob).arrange(DOWN, buff=0.16)
        content.move_to(panel.get_center())
        return VGroup(panel, content)

    def legend_item(self, color: str, label: str) -> VGroup:
        line = Line(LEFT * 0.28, RIGHT * 0.28, color=color, stroke_width=5)
        text = Text(label, font_size=15, color=TEXT)
        return VGroup(line, text).arrange(RIGHT, buff=0.28)

    def takeaway(self, number: str, text: str) -> VGroup:
        circle = Circle(radius=0.18, color=CYAN, stroke_width=2)
        number_mob = Text(number, font_size=14, color=CYAN, weight=BOLD).move_to(circle)
        body = Text(text, font_size=18, color=TEXT)
        return VGroup(VGroup(circle, number_mob), body).arrange(RIGHT, buff=0.22)

    def atp_table(self, rows: list[dict[str, float | str]]) -> VGroup:
        headers = ["Node", "Position", "Peak diff", "0-30 us max error"]
        widths = [1.2, 1.45, 1.65, 2.4]
        x_offsets = np.cumsum([0.0] + widths)
        table_width = float(sum(widths))
        row_height = 0.46
        group = VGroup()

        header_panel = Rectangle(
            width=table_width,
            height=row_height,
            fill_color=PANEL_STROKE,
            fill_opacity=1.0,
            stroke_color=PANEL_STROKE,
            stroke_width=1,
        )
        header_panel.move_to(UP * (row_height * 2.8))
        group.add(header_panel)

        for col_index, header in enumerate(headers):
            x_center = -table_width / 2 + x_offsets[col_index] + widths[col_index] / 2
            header_text = Text(header, font_size=15, color=TEXT, weight=BOLD)
            header_text.move_to(header_panel.get_center() + RIGHT * x_center)
            group.add(header_text)

        for row_index, row in enumerate(rows):
            y_center = row_height * (1.8 - row_index)
            fill = "#151b24" if row_index % 2 == 0 else "#111722"
            panel = Rectangle(
                width=table_width,
                height=row_height,
                fill_color=fill,
                fill_opacity=1.0,
                stroke_color=PANEL_STROKE,
                stroke_width=0.7,
            )
            panel.move_to(UP * y_center)
            group.add(panel)

            values = [
                str(row["node"]),
                f"{float(row['pos_pct']):.0f}%",
                f"{float(row['dif_pico_pct']):+.3f}%",
                f"{float(row['max_err_0a30us_V']):.2f} V",
            ]
            colors = [TEXT, MUTED, GREEN if abs(float(row["dif_pico_pct"])) < 0.03 else YELLOW, CYAN]
            for col_index, value in enumerate(values):
                x_center = -table_width / 2 + x_offsets[col_index] + widths[col_index] / 2
                text = Text(value, font_size=14, color=colors[col_index])
                text.move_to(panel.get_center() + RIGHT * x_center)
                group.add(text)

        caption = Text("Source: output/atp/comparacao_python_atp.csv", font_size=13, color=MUTED)
        caption.next_to(group, DOWN, buff=0.22)
        group.add(caption)
        return group


class InitialDistributionScene(SurgePresentation):
    """Preview helper: renders only the t=0+ initial-distribution slide.

    Iterate on the new scene without rendering the full presentation:
        manim -pql manim_presentation.py InitialDistributionScene
    """

    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.factory = VisualFactory()
        self.data = ProjectDataLoader().load()
        self._base_cfg = None
        self._dist_cache = None
        self.initial_distribution_scene()


class GroundedReturnPreview(SurgePresentation):
    """Preview helper: renders only the grounded time-domain animation with a
    short run time (the surge starting crowded and relaxing toward uniform).
    Iterate with:
        manim -pql manim_presentation.py GroundedReturnPreview
    """

    def construct(self) -> None:
        self.camera.background_color = BACKGROUND
        self.factory = VisualFactory()
        self.data = ProjectDataLoader().load()
        self._base_cfg = None
        self._dist_cache = None
        self.profile_run_time = 8.0
        self.grounded_return_scene(clear_after=False)
