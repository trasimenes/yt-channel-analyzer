// Segment JS library for segmented horizontal bar charts
const SEGMENT_WIDTH = "100%";
const SEGMENT_HEIGHT = "60px";
const palette = [
    "#ffd6e0",  // light pink
    "#ffe9d6",  // peach
    "#fff7c2",  // light yellow
    "#d9f8c4",  // mint green
    "#cde8ff",  // light blue
    "#e6d3ff",  // lavender
    "#d3f3ff",  // aqua
    "#f9d5ff",  // light magenta
    "#e9ecef",  // very light grey-blue
    "#f3ffe3"   // pale lime
];

function buildSegmentBar(element, options) {
    let percentages = getSegmentPercentages(options.data);

    for (let i = 0; i < options.data.length; i++) {
        options.data[i].percent = +percentages[i];
    }

    element.style.width = options.width ? options.width : SEGMENT_WIDTH;
    element.style.height = options.height ? options.height : SEGMENT_HEIGHT;
    element.classList.add("segment-bar");
    let colorIt = getSegmentNextColor();

    for (let item of options.data) {
        let div = document.createElement("div");

        // Prepare wrapper
        const pct = parseFloat(item.percent * 100);
        div.style.width = `${pct}%`;
        if (pct < 5) {
            div.classList.add("segment-small");
        }
        div.style.backgroundColor = item.color
            ? item.color
            : colorIt.next().value;
        div.classList.add("segment-item-wrapper");

        // Percentage span
        let span = document.createElement("span");
        span.textContent = `${prettifySegmentPercentage(item.percent * 100)}%`;
        span.classList.add("segment-item-percentage");

        // Value span
        let valueSpan = document.createElement("span");
        valueSpan.textContent = `${item.value.toLocaleString("en-US")}`;
        valueSpan.classList.add("segment-item-value");

        // Title span
        if (item.title && item.title.length > 0) {
            let titleSpan = document.createElement("span");
            titleSpan.textContent = item.title;
            titleSpan.classList.add("segment-item-title");
            div.appendChild(titleSpan);

            div.title = `${item.title} (${item.value})`;
        }

        div.appendChild(span);
        div.appendChild(valueSpan);
        element.appendChild(div);
    }
}

function prettifySegmentPercentage(percentage) {
    let pretty = parseFloat(percentage).toFixed(2);
    let v = pretty.split(".");
    let final = 0;
    if (v[1]) {
        let digits = v[1].split("");
        if (digits[0] == 0 && digits[1] == 0) {
            final = parseFloat(`${v[0]}`);
        } else {
            final = pretty;
        }
    } else {
        final = parseFloat(v[0]);
    }
    return final;
}

// Accepts an array of chart data, returns an array of percentages
function getSegmentPercentages(data) {
    let sum = getSegmentSum(data);

    return data.map(function (item) {
        return parseFloat(item.value / sum);
    });
}

// Accepts an array of chart data, returns the sum of all values
function getSegmentSum(data) {
    return data.reduce(function (sum, item) {
        return sum + item.value;
    }, 0);
}

function* getSegmentNextColor() {
    let i = 0;
    while (true) {
        yield palette[i];
        i = (i + 1) % palette.length;
    }
} 