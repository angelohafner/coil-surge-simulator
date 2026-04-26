"""
GifGenerator: produces animated GIFs showing surge wave propagation.

GIFs generated
--------------
  1. voltage_wave.gif
       Voltage distribution along the coil vs time.
       Shows the travelling wave and reflections.

  2. heatmap_anim.gif
       Animated 2-D heatmap (position × time), with a vertical time cursor.

  3. comparison_capacitance.gif
       Side-by-side comparison of a low-C and a high-C case,
       illustrating how ground capacitance shapes the wave front.

  4. comparison_model.gif
       Side-by-side comparison of the Pi-model and T-model for
       identical electrical parameters.

All GIFs are saved under output_dir/gifs/.
"""

import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation

_STYLE = {
    "figure.dpi": 120,
    "font.size": 9,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "legend.fontsize": 8,
    "lines.linewidth": 1.5,
}

# Sub-sample factor: 1-in-N frames rendered in the GIF
_SUBSAMPLE = 20
_FPS = 15
_WRITER = "pillow"


class GifGenerator:
    """Creates animated GIFs from one or two sets of simulation results."""

    def __init__(self, output_dir: str):
        self.gif_dir = os.path.join(output_dir, "gifs")
        os.makedirs(self.gif_dir, exist_ok=True)
        plt.rcParams.update(_STYLE)

    # ------------------------------------------------------------------
    # GIF 1: travelling wave animation
    # ------------------------------------------------------------------

    def generate_wave_animation(self, results: dict, filename: str = "voltage_wave.gif") -> None:
        """Animate voltage distribution along the coil over time."""
        print(f"    Building {filename} ...")
        t = results["t"]
        V = results["V_nodes"]              # (n_nodes, n_time)
        pos = results["positions"] * 100    # percent

        cfg = results["config"]
        label = f'{cfg.model_type.upper()}-model ({cfg.n_sections} sec.)'

        # sub-sample time frames
        frame_idx = np.arange(0, len(t), _SUBSAMPLE)
        t_us = t * 1e6

        V_lim = np.max(np.abs(V)) * 1.1

        fig, ax = plt.subplots(figsize=(7, 4))
        (line,) = ax.plot([], [], color="tab:blue", linewidth=2)
        title = ax.set_title("")
        ax.set_xlim(0, 100)
        ax.set_ylim(-V_lim, V_lim)
        ax.set_xlabel("Position along coil [%]")
        ax.set_ylabel("Voltage [V]")
        ax.axhline(0, color="gray", linewidth=0.7, linestyle="--")
        ax.grid(True)
        fig.tight_layout()

        # static annotation for surge impedance, etc.
        ax.text(
            0.98, 0.95, label,
            transform=ax.transAxes,
            ha="right", va="top",
            fontsize=8, color="gray",
        )

        def init():
            line.set_data([], [])
            return (line,)

        def update(fi):
            i = frame_idx[fi]
            line.set_data(pos, V[:, i])
            title.set_text(f"Voltage Distribution   t = {t_us[i]:.2f} µs")
            return (line, title)

        anim = animation.FuncAnimation(
            fig, update, init_func=init,
            frames=len(frame_idx), blit=True, interval=1000 / _FPS
        )
        path = os.path.join(self.gif_dir, filename)
        anim.save(path, writer=_WRITER, fps=_FPS)
        plt.close(fig)
        print(f"      -> {path}")

    # ------------------------------------------------------------------
    # GIF 2: heatmap animation with time cursor
    # ------------------------------------------------------------------

    def generate_heatmap_animation(
        self, results: dict, filename: str = "heatmap_anim.gif"
    ) -> None:
        """Animated heatmap: full time×position map + travelling cursor line."""
        print(f"    Building {filename} ...")
        t = results["t"]
        V = results["V_nodes"]              # (n_nodes, n_time)
        pos = results["positions"] * 100
        t_us = t * 1e6

        cfg = results["config"]

        frame_idx = np.arange(0, len(t), _SUBSAMPLE)
        vmax = np.max(np.abs(V))

        fig, (ax_map, ax_wave) = plt.subplots(
            1, 2, figsize=(11, 4.5),
            gridspec_kw={"width_ratios": [2, 1.3]}
        )

        # --- static heatmap ---
        im = ax_map.pcolormesh(
            t_us, pos, V,
            cmap="RdBu_r", vmin=-vmax, vmax=vmax, shading="auto"
        )
        cbar = fig.colorbar(im, ax=ax_map)
        cbar.set_label("Voltage [V]", fontsize=8)
        ax_map.set_xlabel("Time [µs]")
        ax_map.set_ylabel("Position [%]")
        ax_map.set_title(
            f"{cfg.model_type.upper()}-model Heatmap"
        )

        # cursor line on heatmap
        (cursor,) = ax_map.plot([], [], color="yellow", linewidth=1.5, linestyle="--")

        # --- right panel: instantaneous profile ---
        (line_wave,) = ax_wave.plot([], [], color="tab:blue", linewidth=2)
        title_wave = ax_wave.set_title("")
        ax_wave.set_xlim(-vmax * 1.1, vmax * 1.1)
        ax_wave.set_ylim(0, 100)
        ax_wave.set_xlabel("Voltage [V]")
        ax_wave.set_ylabel("Position [%]")
        ax_wave.axvline(0, color="gray", linewidth=0.7, linestyle="--")
        ax_wave.grid(True)

        fig.tight_layout()

        def init():
            cursor.set_data([], [])
            line_wave.set_data([], [])
            return cursor, line_wave

        def update(fi):
            i = frame_idx[fi]
            ti = t_us[i]
            cursor.set_data([ti, ti], [0, 100])
            line_wave.set_data(V[:, i], pos)
            title_wave.set_text(f"t = {ti:.2f} µs")
            return cursor, line_wave, title_wave

        anim = animation.FuncAnimation(
            fig, update, init_func=init,
            frames=len(frame_idx), blit=True, interval=1000 / _FPS
        )
        path = os.path.join(self.gif_dir, filename)
        anim.save(path, writer=_WRITER, fps=_FPS)
        plt.close(fig)
        print(f"      -> {path}")

    # ------------------------------------------------------------------
    # GIF 3 & 4: side-by-side comparison
    # ------------------------------------------------------------------

    def generate_comparison_animation(
        self,
        results_a: dict,
        results_b: dict,
        label_a: str,
        label_b: str,
        filename: str = "comparison.gif",
    ) -> None:
        """
        Animate the voltage distribution for two cases side by side.
        Both results must share the same time array (same dt, t_total).
        """
        print(f"    Building {filename} ...")

        t = results_a["t"]
        t_us = t * 1e6
        Va = results_a["V_nodes"]
        Vb = results_b["V_nodes"]
        pos_a = results_a["positions"] * 100
        pos_b = results_b["positions"] * 100

        frame_idx = np.arange(0, len(t), _SUBSAMPLE)
        vmax = max(np.max(np.abs(Va)), np.max(np.abs(Vb))) * 1.1

        fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11, 4))
        for ax, label, color in zip(
            (ax_a, ax_b), (label_a, label_b), ("tab:blue", "tab:orange")
        ):
            ax.set_xlim(0, 100)
            ax.set_ylim(-vmax, vmax)
            ax.set_xlabel("Position [%]")
            ax.set_ylabel("Voltage [V]")
            ax.axhline(0, color="gray", linewidth=0.7, linestyle="--")
            ax.grid(True)
            ax.text(
                0.5, 0.96, label,
                transform=ax.transAxes,
                ha="center", va="top",
                fontsize=9, color=color, fontweight="bold",
            )

        (line_a,) = ax_a.plot([], [], color="tab:blue", linewidth=2)
        (line_b,) = ax_b.plot([], [], color="tab:orange", linewidth=2)
        sup = fig.suptitle("", fontsize=11)
        fig.tight_layout()

        def init():
            line_a.set_data([], [])
            line_b.set_data([], [])
            return line_a, line_b

        def update(fi):
            i = frame_idx[fi]
            line_a.set_data(pos_a, Va[:, i])
            line_b.set_data(pos_b, Vb[:, i])
            sup.set_text(f"t = {t_us[i]:.2f} µs")
            return line_a, line_b, sup

        anim = animation.FuncAnimation(
            fig, update, init_func=init,
            frames=len(frame_idx), blit=True, interval=1000 / _FPS
        )
        path = os.path.join(self.gif_dir, filename)
        anim.save(path, writer=_WRITER, fps=_FPS)
        plt.close(fig)
        print(f"      -> {path}")

    # ------------------------------------------------------------------
    # Convenience: generate all 4 GIFs
    # ------------------------------------------------------------------

    def generate_all(
        self,
        results_pi: dict,
        results_t: dict,
        results_low_c: dict,
        results_high_c: dict,
        label_low_c: str,
        label_high_c: str,
    ) -> None:
        print("  Generating GIFs ...")
        self.generate_wave_animation(results_pi,  "voltage_wave_pi.gif")
        self.generate_wave_animation(results_t,   "voltage_wave_t.gif")
        self.generate_heatmap_animation(results_pi, "heatmap_anim.gif")
        self.generate_comparison_animation(
            results_low_c, results_high_c,
            label_low_c, label_high_c,
            "comparison_capacitance.gif",
        )
        self.generate_comparison_animation(
            results_pi, results_t,
            f'Pi-model ({results_pi["config"].n_sections} sec.)',
            f'T-model  ({results_t["config"].n_sections} sec.)',
            "comparison_model.gif",
        )
