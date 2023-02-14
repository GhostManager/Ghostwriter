# 3rd Party Libraries
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

MEAN = "mean"
SD = "sd"
BLUE = "#14588F"
ORANGE = "#EC6403"
FONT_FAMILY = "Liberation Sans Narrow"


def _get_regions(x_normdist, plotdata):
    # create logical lists
    average = (x_normdist >= (plotdata[MEAN] - 1 * plotdata[SD])) & (
        x_normdist <= (plotdata[MEAN] + 1 * plotdata[SD])
    )
    above_and_below_average = (x_normdist >= (plotdata[MEAN] - 2 * plotdata[SD])) & (
        x_normdist < (plotdata[MEAN] - 1 * plotdata[SD])
    ) | (x_normdist > (plotdata[MEAN] + 1 * plotdata[SD])) & (
        x_normdist <= (plotdata[MEAN] + 2 * plotdata[SD])
    )
    far_above_and_below_average = (x_normdist >= (plotdata[MEAN] - 3 * plotdata[SD])) & (
        x_normdist < (plotdata[MEAN] - 2 * plotdata[SD])
    ) | (x_normdist > (plotdata[MEAN] + 2 * plotdata[SD])) & (
        x_normdist <= (plotdata[MEAN] + 3 * plotdata[SD])
    )
    return [average, above_and_below_average, far_above_and_below_average]


def _create_bell_curve(ax, x_normdist, plotdata):
    # Code came from https://stackoverflow.com/questions/54422579/efficient-way-of-shading-multiple-regions-under-curve
    # Orange bell line
    y = norm.pdf(x_normdist, plotdata[MEAN], plotdata[SD])
    ax.plot(x_normdist, y, color=ORANGE)

    regions = _get_regions(x_normdist, plotdata)
    # set alpha values - different shades for regions
    alpha_values = [1, 0.65, 0.15]

    # plot regions with corresponding alpha values
    for idx, region in enumerate(regions):
        y = norm.pdf(x_normdist, plotdata[MEAN], plotdata[SD])
        ax.fill_between(
            x_normdist, y, color=BLUE, alpha=alpha_values[idx], where=regions[idx]
        )


def _label_x_axis(ax):
    locs = ax.get_xticks()
    labels = ax.get_xticklabels()
    labels = [item.get_text() for item in labels]

    labels[1] = "-3\n|\nFar Below Average\n"
    labels[2] = "-2"
    labels[3] = "-1"
    labels[4] = "0\n|\nAverage\n"
    labels[5] = "1"
    labels[6] = "2"
    labels[7] = "3\n|\nFar Above Average\n"
    ax.set_xticks(
        ticks=locs,
        labels=labels,
        fontsize=11,
        fontfamily=FONT_FAMILY,
        fontweight="bold",
        color=BLUE,
    )


def _modify_graph_display(ax):
    # Hide all spines except bottom
    ax.spines.right.set_visible(False)
    ax.spines.top.set_visible(False)
    ax.spines.left.set_visible(False)
    ax.spines.bottom.set_color(BLUE)
    ax.spines.bottom.set_linewidth(2)

    # Hide y axis ticks
    ax.set_yticks([])


def _annotate_score(sd_score, y, ax, x_shift=0, y_shift=0):
    # Format the SD score as a string
    # Calculate the coordinates to angle the arrow and orange bubble based on negative and positive values
    bubble_x_pad = 0.75 + x_shift
    bubble_y_pad = 0.12 + y_shift
    bubble_coors = (sd_score + bubble_x_pad, y + bubble_y_pad)

    arrow_x_pad = 0.55 + x_shift
    arrow_y_pad = 0.09 + y_shift
    arrow_coors = (sd_score + arrow_x_pad + 0.25, y + arrow_y_pad)

    if sd_score > 0:
        sd_score_str = "+" + str(sd_score)
    elif sd_score == 0:
        sd_score_str = str("+0.0")
    else:
        # Subtract the x coors for both arrow and bubble when negative
        bubble_coors = (sd_score - bubble_x_pad, y + bubble_y_pad)
        arrow_coors = (sd_score - arrow_x_pad - 0.25, y + arrow_y_pad)
        sd_score_str = str(sd_score)

    t = ax.text(
        bubble_coors[0],
        bubble_coors[1],
        sd_score_str,
        ha="center",
        va="center",
        size=12,
        color="white",
        fontfamily=FONT_FAMILY,
        fontweight="extra bold",
        bbox=dict(boxstyle="Round,pad=0.4", fc=ORANGE, ec=ORANGE, lw=2),
    )
    ax.annotate(
        "",
        (sd_score, y),
        xytext=arrow_coors,
        arrowprops=dict(arrowstyle="-", color=ORANGE, lw=2),
    )


def _plot_score(sd_score, ax, plotdata, x_shift=0, y_shift=0):
    sd_score = round(sd_score, 1)
    y = norm.pdf(sd_score, plotdata[MEAN], plotdata[SD])
    ax.scatter(sd_score, y, s=64, color="white", ec=ORANGE, zorder=10)
    _annotate_score(sd_score, y, ax, x_shift, y_shift)


def build_sd_graph(sd_score):
    # Mean is 0 = Average; each x axis tick is std of 1
    plotdata = {MEAN: 0, SD: 1}

    # plot normal distribution
    x_normdist = np.linspace(
        plotdata[MEAN] - 3 * plotdata[SD], plotdata[MEAN] + 3 * plotdata[SD], 100
    )

    # Axis object is used a lot it handles threading better than plt. calls
    fig, ax = plt.subplots(1)
    _create_bell_curve(ax, x_normdist, plotdata)

    # Set the x ticks to the labelling we want
    _label_x_axis(ax)
    _modify_graph_display(ax)
    _plot_score(sd_score, ax, plotdata)

    # Shrink figure to be close to current size in Word template
    fig.set_size_inches(4.5, 1.85)
    # Think of DPI as zooming in on the image making it easier to see
    fig.set_dpi(150)
    return fig
