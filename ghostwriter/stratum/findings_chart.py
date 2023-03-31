# Standard Libraries
from enum import Enum

# 3rd Party Libraries
import pandas as pd

# Custom code
from .enums import Severity


class CalcCol(Enum):
    TOTAL = "Total"
    WEIGHT = "Weight"


FONT_FAMILY = "Arial Narrow"
FONT_SIZE = 9


def _build_axis_style(ax, max_y):
    labelpad = 10
    label_font_size = FONT_SIZE + 3
    ax.set_xlabel(
        "Findings Category",
        fontfamily=FONT_FAMILY,
        fontsize=label_font_size,
        fontweight="bold",
        labelpad=labelpad,
    )
    ax.set_ylabel(
        "Total Number of Findings",
        fontfamily=FONT_FAMILY,
        fontsize=label_font_size,
        fontweight="bold",
        labelpad=labelpad,
    )
    ax.set_yticks(range(0, max_y))

    # Hide the right and top spines
    ax.spines.right.set_visible(False)
    ax.spines.top.set_visible(False)
    spine_color = "#868686"
    ax.spines.left.set_color(spine_color)
    ax.spines.bottom.set_color(spine_color)


def _build_legend_style(ax):
    # Set the right font for the legend, remove frame, horizontal legend,
    # and anchor in the upper right corner outside the bar chart to prevent bars being close to legend
    h, l = ax.get_legend_handles_labels()
    legend = ax.legend(
        reversed(h),
        reversed(l),
        prop={"family": FONT_FAMILY, "size": FONT_SIZE + 2},
        loc="upper right",
        ncol=5,
        columnspacing=1,
        handletextpad=-0.5,
        bbox_to_anchor=(1, 1.2),
    )
    legend.set_frame_on(False)
    for h in legend.legendHandles:
        h.set_width(8)


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
            fontsize=FONT_SIZE + 3,
        )


def build_bar_chart(report_data):
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
    # Font size subtraction is used to prevent overlapping x-axis labels
    # When finding categories exceeds 6, we need to shrink the font size some more on the labels
    if len(df.index) > 6:
        # Subtracting by 0.5 on font size is the best when all finding categories are present to prevent overlapping
        label_font_size = FONT_SIZE - 0.5
    else:
        label_font_size = FONT_SIZE

    ax = df.plot(
        x=category_label,
        legend="reverse",
        kind="bar",
        fontsize=label_font_size,
        stacked=True,
        rot=0,
        # Color scheme came from
        # https://miro.medium.com/v2/resize:fit:500/format:webp/1*msOeUmFxdojyrur1kqxwaw.png
        color={
            Severity.BP.value: "#4E81BD",
            Severity.LOW.value: "#8BC53F",
            Severity.MED.value: "#F6941F",
            Severity.HIGH.value: "#F0582B",
            Severity.CRIT.value: "#DE0604",
        },
    )

    _build_axis_style(ax, max_y)
    fig = ax.get_figure()

    # Shrink figure to be close to current size in Word template
    # Current literals set make the figure fit on the page correctly
    fig.set_size_inches(10, 2.9)
    # Think of DPI as zooming in on the image making it easier to see
    fig.set_dpi(200)

    _build_legend_style(ax)
    _label_bars(ax)
    return fig


def build_pie_chart(report_data, total_findings):
    df = pd.DataFrame(report_data)
    # Make the category label the index and then the only column in the frame is the percentage
    df = df.set_index(0)
    df = round(df.sum(axis=1, numeric_only=True) / total_findings * 100, 0).astype(int)
    # Sorting also helps to prevent overlapping on the labels
    df = df.sort_index()
    ax = df.plot(
        kind="pie",
        radius=1.5,
        y=1,
        legend=False,
        wedgeprops={"linewidth": 1, "edgecolor": "white", "antialiased": True},
        autopct="%1.0f%%",
        pctdistance=0.8,
        startangle=145,
        labeldistance=1.3,
        # Color scheme came from
        # https://medium.com/@alrieristivan/guide-to-colour-wheel-7ea66881a83a
        colors=[
            "#662D91",
            "#1075BD",
            "#BE1E2E",
            "#0D9444",
            "#FCB040",
            "#10A89E",
            "#8BC53F",
            "#D91A5C",
            "#F6941F",
            "#F0582B",
            "#BE1E2E",
            "#262262",
        ],
        textprops={
            "size": FONT_SIZE,
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
    fig.set_figheight(2.8)
    fig.set_dpi(200)
    return fig
