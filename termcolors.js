function ddw_colorstr_to_css(colorstr) {
    var cssclass = ""; // = [];
    var i = 0;
    colorstr.split(" ").forEach((x) => {
        if (x == "fg") {
            i = 0;
            return;
        } else if (x == "on" || x == "bg") {
            i = 1;
            return;
        }

        if (x == "bold" || x == "underline" || x == "italic") {
            cssclass += " " + x;
        } else {
            if (i == 0) {
                cssclass += " fg" + x;
            } else {
                cssclass += " bg" + x;
             }
        }
    });

    console.log(colorstr, cssclass)
    return cssclass;
}
