"""
Sankey / Flow diagram with proper bezier flow bands.

• Bivariate context  (no grp_col) → two-column layout:   X  →  Y
• Trivariate context (has grp_col) → three-column layout: X  →  Y  →  Group

Node bars are neutral gray.
Flow bands are coloured by the first-column (X) source category with alpha 0.42.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES

# ── Layout constants ──────────────────────────────────────────────────────────
NODE_COLOR  = "#9CA3AF"    # neutral gray for all node bars
NODE_W      = 0.028        # node bar width in axes-data coords
FLOW_ALPHA  = 0.42
NODE_GAP    = 0.010        # vertical gap between stacked nodes
Y_MIN       = 0.06
Y_MAX       = 0.88


class Sankey(BaseChart):
    CHART_ID       = "sankey"
    DISPLAY_NAME   = "Sankey Diagram"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",         "type": "text",   "default": ""},
            "palette": {"label": "Colour palette", "type": "choice", "default": MPL_DEFAULT_PALETTE,
                        "choices": PALETTE_CHOICES},
            **BaseChart._title_style_options(),
        }

    # ── Public render ─────────────────────────────────────────────────────────

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.set_facecolor(self._chart_bg())
        fig.patch.set_facecolor(self._chart_bg())

        x_col   = selection.x_var
        y_col   = selection.y_var
        grp_col = selection.group_var

        # Decide columns
        if grp_col and grp_col in df.columns:
            cols = [x_col, y_col, grp_col]
        else:
            cols = [x_col, y_col]

        sub = df[cols].dropna().astype(str)

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        # Warn if too many categories
        for col in cols:
            if sub[col].nunique() > 12:
                ax.text(
                    0.5, 0.5,
                    f"'{col}' has {sub[col].nunique()} categories.\n"
                    "Sankey works best with ≤ 12 per column.\n"
                    "Use the Clean button to filter or merge categories.",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color="#64748B", wrap=True,
                )
                return

        n_cols = len(cols)
        # Column x-centres (2-col or 3-col)
        if n_cols == 2:
            col_xs = [0.18, 0.82]
        else:
            col_xs = [0.13, 0.50, 0.87]

        # ── Assign colours to first-column categories ────────────────────────
        palette  = self._opt("palette") or MPL_DEFAULT_PALETTE
        src_cats = sorted(sub[cols[0]].unique(), key=str)
        n_src    = len(src_cats)
        try:
            cmap      = plt.cm.get_cmap(palette, max(n_src, 2))
            src_colors = {c: cmap(i / max(n_src - 1, 1)) for i, c in enumerate(src_cats)}
        except Exception:
            src_colors = {c: "#2563EB" for c in src_cats}

        # ── Build node counts for each column ────────────────────────────────
        node_counts: list[dict[str, int]] = []
        for col in cols:
            vc = sub[col].value_counts().to_dict()
            node_counts.append(vc)

        # ── Layout: compute (y_bottom, y_top) for every node ────────────────
        node_positions = self._layout_nodes(node_counts)

        # ── Draw node bars ───────────────────────────────────────────────────
        for ci, col in enumerate(cols):
            cx  = col_xs[ci]
            x0  = cx - NODE_W / 2
            for cat, (yb, yt) in node_positions[ci].items():
                ax.add_patch(plt.Rectangle(
                    (x0, yb), NODE_W, yt - yb,
                    facecolor=NODE_COLOR, edgecolor="white", linewidth=0.8,
                    zorder=3,
                ))
            # Column header
            ax.text(cx, 0.94, col, ha="center", va="bottom",
                    fontsize=9, fontweight="bold", color="#374151", zorder=5)

        # ── Draw node labels ─────────────────────────────────────────────────
        for ci, col in enumerate(cols):
            cx  = col_xs[ci]
            for cat, (yb, yt) in node_positions[ci].items():
                ymid = (yb + yt) / 2
                if ci == 0:                          # left column → label on left
                    ax.text(cx - NODE_W / 2 - 0.012, ymid, str(cat),
                            ha="right", va="center", fontsize=8, color="#374151", zorder=5)
                else:                                # other columns → label on right
                    ax.text(cx + NODE_W / 2 + 0.012, ymid, str(cat),
                            ha="left", va="center", fontsize=8, color="#374151", zorder=5)

        # ── Draw flows for each adjacent-column segment ──────────────────────
        for seg in range(n_cols - 1):
            left_col  = cols[seg]
            right_col = cols[seg + 1]
            lx_right  = col_xs[seg]     + NODE_W / 2   # right edge of left node bar
            rx_left   = col_xs[seg + 1] - NODE_W / 2   # left  edge of right node bar

            flow_df = (sub.groupby([left_col, right_col])
                          .size()
                          .reset_index(name="n"))

            left_pos  = node_positions[seg]
            right_pos = node_positions[seg + 1]

            # Cursors: next available y at the bottom of each node
            left_cur  = {cat: yb for cat, (yb, _)  in left_pos.items()}
            right_cur = {cat: yb for cat, (yb, _)  in right_pos.items()}

            # Sort flows for deterministic stacking (large flows first per source)
            flow_df = flow_df.sort_values([left_col, "n"], ascending=[True, False])

            for _, row in flow_df.iterrows():
                lcat = row[left_col]
                rcat = row[right_col]
                count = row["n"]

                if lcat not in left_pos or rcat not in right_pos:
                    continue

                # Height of this flow slice in left node
                l_h_total  = left_pos[lcat][1]  - left_pos[lcat][0]
                l_n_total  = node_counts[seg][lcat]
                flow_l_h   = (count / l_n_total) * l_h_total

                # Height of this flow slice in right node
                r_h_total  = right_pos[rcat][1]  - right_pos[rcat][0]
                r_n_total  = node_counts[seg + 1][rcat]
                flow_r_h   = (count / r_n_total) * r_h_total

                ly0 = left_cur[lcat]
                ly1 = ly0 + flow_l_h
                ry0 = right_cur[rcat]
                ry1 = ry0 + flow_r_h

                left_cur[lcat]  = ly1
                right_cur[rcat] = ry1

                # Flow colour = first-column source category
                if seg == 0:
                    color = src_colors.get(lcat, "#94A3B8")
                else:
                    # For later segments, use dominant X-source of the left_col category
                    color = self._dominant_src_color(sub, cols, lcat, src_colors)

                self._draw_bezier_band(ax, lx_right, ly0, ly1, rx_left, ry0, ry1,
                                       color, FLOW_ALPHA)

        title = self._opt("title") or (
            f"Flow: {x_col} → {y_col} → {grp_col}"
            if n_cols == 3
            else f"Flow: {x_col} → {y_col}"
        )
        self._apply_title(ax, title)
        fig.tight_layout()

    # ── Private helpers ───────────────────────────────────────────────────────

    def _layout_nodes(
        self,
        node_counts: list[dict[str, int]],
    ) -> list[dict[str, tuple[float, float]]]:
        """
        Return, for each column, a dict mapping category → (y_bottom, y_top).
        Nodes sorted alphabetically, stacked bottom-to-top with small gaps.
        """
        avail = Y_MAX - Y_MIN
        result: list[dict[str, tuple[float, float]]] = []

        for cnt_dict in node_counts:
            total    = sum(cnt_dict.values()) or 1
            cats     = sorted(cnt_dict.keys(), key=str)
            n        = len(cats)
            gap_tot  = max(n - 1, 0) * NODE_GAP
            node_tot = avail - gap_tot

            positions: dict[str, tuple[float, float]] = {}
            y = Y_MIN
            for cat in cats:
                h = (cnt_dict[cat] / total) * node_tot
                positions[cat] = (y, y + h)
                y += h + NODE_GAP
            result.append(positions)

        return result

    def _dominant_src_color(
        self,
        sub: pd.DataFrame,
        cols: list[str],
        mid_cat: str,
        src_colors: dict,
    ) -> tuple:
        """For a middle-column category, find the most common first-column source."""
        mid_col = cols[1]
        src_col = cols[0]
        counts  = sub[sub[mid_col] == mid_cat][src_col].value_counts()
        if counts.empty:
            return (0.58, 0.64, 0.65, 1.0)   # fallback gray
        return src_colors.get(counts.index[0], (0.58, 0.64, 0.65, 1.0))

    @staticmethod
    def _draw_bezier_band(
        ax,
        x0: float, y0_bot: float, y0_top: float,
        x1: float, y1_bot: float, y1_top: float,
        color, alpha: float,
    ) -> None:
        """Fill a cubic-bezier band between two vertical segments."""
        cx = (x0 + x1) / 2
        verts = [
            (x0, y0_top),          # MOVETO  — top-left corner
            (cx, y0_top),          # CURVE4 CP1
            (cx, y1_top),          # CURVE4 CP2
            (x1, y1_top),          # CURVE4 end — top-right corner
            (x1, y1_bot),          # LINETO — bottom-right corner
            (cx, y1_bot),          # CURVE4 CP1
            (cx, y0_bot),          # CURVE4 CP2
            (x0, y0_bot),          # CURVE4 end — bottom-left corner
            (x0, y0_top),          # CLOSEPOLY
        ]
        codes = [
            Path.MOVETO,
            Path.CURVE4, Path.CURVE4, Path.CURVE4,
            Path.LINETO,
            Path.CURVE4, Path.CURVE4, Path.CURVE4,
            Path.CLOSEPOLY,
        ]
        patch = PathPatch(
            Path(verts, codes),
            facecolor=color,
            edgecolor="none",
            alpha=alpha,
            zorder=2,
        )
        ax.add_patch(patch)
