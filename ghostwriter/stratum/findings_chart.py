# Standard Libraries
from enum import Enum

# 3rd Party Libraries
import pandas as pd

# Custom code
from .enums import Severity


class CalcCol(Enum):
    TOTAL = "Total"
    WEIGHT = "Weight"


FONT_FAMILY = "Liberation Sans Narrow"
FONT_SIZE = 8
BACKGROUND_COLOR = "#F6F5EE"


def _build_axis_style(ax, max_y):
    ax.set_xlabel(
        "Findings Category", fontfamily=FONT_FAMILY, fontsize=FONT_SIZE, fontweight="bold"
    )
    ax.set_ylabel(
        "Total Number of Findings",
        fontfamily=FONT_FAMILY,
        fontsize=FONT_SIZE,
        fontweight="bold",
    )
    ax.set_facecolor(BACKGROUND_COLOR)
    ax.set_yticks(range(0, max_y))

    # Hide the right and top spines
    ax.spines.right.set_visible(False)
    ax.spines.top.set_visible(False)
    spine_color = "#868686"
    ax.spines.left.set_color(spine_color)
    ax.spines.bottom.set_color(spine_color)


def _build_legend_style(ax, fig):
    # Set the right font for the legend, remove frame, and anchor in the upper right corner
    h, l = ax.get_legend_handles_labels()
    legend = ax.legend(
        reversed(h), reversed(l), prop={"family": FONT_FAMILY, "size": FONT_SIZE}
    )
    legend.set_frame_on(False)
    for h in legend.legendHandles:
        h.set_width(8)
    legend.set_bbox_to_anchor((1, 1), fig.transFigure)


def _label_bars(ax):
    # Loop through each category and do not display 0 labels in chart
    suppress_zero = 0
    for container in ax.containers:
        labels = [int(v) if v != suppress_zero else "" for v in container.datavalues]
        ax.bar_label(
            container,
            labels=labels,
            label_type="center",
            color="white",
            fontweight="bold",
            fontfamily=FONT_FAMILY,
            fontsize=FONT_SIZE,
        )


def build_chart(report_data):
    category_label = "Category"
    df = pd.DataFrame(
        report_data,
        columns=[
            category_label,
            Severity.BP.value,
            Severity.LOW.value,
            Severity.MED.value,
            Severity.HIGH.value,
            Severity.CRIT.value,
        ],
    )

    # Drops rows that have no findings
    df2 = df.loc[:, df.columns != category_label]
    df = df.loc[(df2 != 0).any(axis=1)]

    # Calculate the totals for each category and weight
    df[CalcCol.TOTAL.value] = df.sum(axis=1, numeric_only=True)
    df[CalcCol.WEIGHT.value] = (
        (df[Severity.BP.value] * 1)
        + (df[Severity.LOW.value] * 2)
        + (df[Severity.MED.value] * 3)
        + (df[Severity.HIGH.value] * 4)
        + (df[Severity.CRIT.value] * 5)
    )
    # Sorts the graph by weight
    df = df.sort_values([CalcCol.TOTAL.value, CalcCol.WEIGHT.value], ascending=False)

    # Get the max finding count and add spacing for the y axis
    max_y = int(df[CalcCol.TOTAL.value].max()) + 2
    # Drop the calc columns as they aren't used in the graph and the color field will throw an error if they are present
    df = df.drop(columns=[CalcCol.TOTAL.value, CalcCol.WEIGHT.value])

    # Digital Color Meter was used to get exact color codes from Excel chart
    # font size - 2 is used to prevent overlapping x-axis labels
    ax = df.plot(
        x=category_label,
        legend="reverse",
        kind="bar",
        fontsize=FONT_SIZE - 2,
        stacked=True,
        rot=0,
        color={
            Severity.BP.value: "#4F81BD",
            Severity.LOW.value: "#008001",
            Severity.MED.value: "#E46C0B",
            Severity.HIGH.value: "#FF0000",
            Severity.CRIT.value: "#A60023",
        },
    )

    _build_axis_style(ax, max_y)
    fig = ax.get_figure()
    fig.set_facecolor(BACKGROUND_COLOR)

    # Shrink figure to be close to current size in Word template
    # Current literals set make the figure fit on the page correctly
    fig.set_size_inches(6.3, 2.8)
    # Think of DPI as zooming in on the image making it easier to see
    fig.set_dpi(200)

    _build_legend_style(ax, fig)
    _label_bars(ax)
    return fig


def build_pie_chart(report_data, total_findings):
    df = pd.DataFrame(report_data)
    # Make the category label the index and then the only column in the frame is the percentage
    df = df.set_index(0)
    df = round(df.sum(axis=1, numeric_only=True) / total_findings * 100, 0).astype(int)
    ax = df.plot(
        kind="pie",
        radius=1.5,
        y=1,
        legend=False,
        wedgeprops={"linewidth": 1, "edgecolor": "white", "antialiased": True},
        autopct="%1.0f%%",
        pctdistance=0.8,
        figsize=(10, 5),
        startangle=0,
        labeldistance=1.2,
        # TODO Update colors based on what John wants when he gets back to me
        colors=["#4F81BD", "#008001", "#E46C0B", "#FF0000", "#A60023"],
        textprops={
            "size": 11,
            "weight": "bold",
            "family": FONT_FAMILY,
            "horizontalalignment": "center",
        },
    )
    ax.set_ylabel(None)

    for text in ax.texts:
        if "%" in text.get_text():
            text.set_color("white")

    fig = ax.get_figure()
    fig.set_facecolor(BACKGROUND_COLOR)
    fig.set_dpi(100)
    return fig
