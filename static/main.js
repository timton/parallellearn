/* appends comment to board */


/* upon submitting the practice line , removes the blur from the translated line*/
function removeBlur() {

    // remove the blur from the translated line
    document.getElementById("to_line").removeAttribute("class");

    // move focus to the 'next line' button
    document.getElementById("next_line").focus();

    // get the index of the current line, increment it
    var x = document.getElementById("next_line").getAttribute("value");
    var y = parseInt(x);

    // once line unblurred, count current line as passed
    // update the save progress button with the new values, if on actual project practice, not random
    // https://stackoverflow.com/questions/5629684/how-to-check-if-element-exists-in-the-visible-dom
    var save_possible = document.getElementById("save_progress");
    if (save_possible !== null) {
        var save_progress_old = document.getElementById("save_progress").getAttribute("value");
        var save_progress_array = save_progress_old.split(",");
        var save_progress_new = y.toString() + "," + save_progress_array[1] + "," + save_progress_array[2] + "," + save_progress_array[3];
        document.getElementById("save_progress").removeAttribute("value");
        document.getElementById("save_progress").setAttribute("value", save_progress_new);
    }
}

/* displays the next line */
function displayNextLine(from_lines, to_lines, size) {

    // get the index of the current line, increment it
    var x = document.getElementById("next_line").getAttribute("value");
    var y = parseInt(x);

    // update the progress bar first (it progresses only once the next button is hit)
    document.getElementById("progress_bar").removeAttribute("value");
    document.getElementById("progress_bar").setAttribute("value", y);

    y += 1;

    // alert, if no more lines
    if (y > size) {
        alert("You finished!");
        return;
    }

    // update the progress line
    var progress_line1 = "Line ";
    var progress_line2 = y.toString();
    var progress_line3 = "/";
    var progress_line4 = size.toString();
    var progress_line = progress_line1 + progress_line2 + progress_line3 + progress_line4;
    document.getElementById("progress_line").innerHTML = progress_line;

    // update the edit buttons with the new id values
    var from_line_id = from_lines[y - 1].id.toString();
    var to_line_id = to_lines[y - 1].id.toString();
    var edit_from_line = from_line_id + "," + to_line_id;
    var edit_to_line = to_line_id + "," + from_line_id;
    document.getElementById("edit_from_line").removeAttribute("value");
    document.getElementById("edit_from_line").setAttribute("value", edit_from_line);
    document.getElementById("edit_to_line").removeAttribute("value");
    document.getElementById("edit_to_line").setAttribute("value", edit_to_line);

    // get the next from & to lines
    var from_line = from_lines[y - 1];
    var to_line = to_lines[y - 1];

    // display the next from & to lines, empty the practice field
    from_line_tag = document.getElementById("from_line");
    from_line_tag.innerHTML = from_line.line;
    to_line_tag = document.getElementById("to_line");
    to_line_tag.innerHTML = to_line.line;
    practice_line_tag = document.getElementById("practice_line");
    practice_line_tag.value="";

    // set the incremented index as the value of the next line button
    document.getElementById("next_line").removeAttribute("value");
    document.getElementById("next_line").setAttribute("value", y);

    // blur the to line
    var line_to_blur = document.getElementById("to_line");
    line_to_blur.setAttribute("class", "blurry");

    // return focus to the practice line
    practice_line_tag.focus();
}

// Get specific starting point when preparing to practice
function getStartingPoint() {

    // Container <div> where dynamic content will be placed
    var specific_start_container = document.getElementById("specific_start_container");

    // ensure option "specific starting point"
    var start = document.getElementById("start_from").value;
    var start1 = start.toLowerCase();
    var start2 = "from a specific point";
    var n = start1.localeCompare(start2)
    if (n != 0) {

        // Clear previous contents of the container
        while (specific_start_container.hasChildNodes()) {
            specific_start_container.removeChild(specific_start_container.lastChild);
        }

        window.alert('Only for specific starting point.');
        return;
    }

    // Clear previous contents of the container
    while (specific_start_container.hasChildNodes()) {
        specific_start_container.removeChild(specific_start_container.lastChild);
    }

    // Create an label and input for specific starting point
    var specific_start_label = document.createElement("label");
    specific_start_label.setAttribute("class", "sr-only");
    specific_start_label.setAttribute("for", "specific_start");
    specific_start_label.innerHTML = "Starting line";

    var specific_start_input = document.createElement("input");
    specific_start_input.autofocus;
    specific_start_input.setAttribute("class", "form-control");
    specific_start_input.name = "specific_start";
    specific_start_input.id = "specific_start";
    specific_start_input.placeholder = "Starting line";
    specific_start_input.type = "number";
    specific_start_input.setAttribute("min", "1");

    // add the newly created tags
    specific_start_container.appendChild(document.createElement("br"));
    specific_start_container.appendChild(specific_start_label);
    specific_start_container.appendChild(specific_start_input);
    specific_start_container.appendChild(document.createElement("br"));
}

// Adding input elements dynamically to form
// https://stackoverflow.com/questions/14853779/adding-input-elements-dynamically-to-form
function addEpisode(n){

    // uploading new project scenario
    if (n == 1) {

        // Container <div> where dynamic content will be placed
        var upload_episode_container = document.getElementById("upload_episode_container");

        // ensure type series
        var type = document.getElementById("type").value;
        var type1 = type.toLowerCase();
        var type2 = "series";
        var n = type1.localeCompare(type2)
        if (n != 0) {

            // Clear previous contents of the container
            while (upload_episode_container.hasChildNodes()) {
                upload_episode_container.removeChild(upload_episode_container.lastChild);
            }

            window.alert('Only for Series.');
            return;
        }

        // Clear previous contents of the container
        while (upload_episode_container.hasChildNodes()) {
            upload_episode_container.removeChild(upload_episode_container.lastChild);
        }


        // Create an label and input for season and episode
        var add_season_label = document.createElement("label");
        add_season_label.setAttribute("class", "sr-only");
        add_season_label.setAttribute("for", "season");
        add_season_label.innerHTML = "Season";

        var add_season_input = document.createElement("input");
        add_season_input.autofocus;
        add_season_input.setAttribute("class", "form-control");
        add_season_input.name = "season";
        add_season_input.id = "season";
        add_season_input.placeholder = "Season";
        add_season_input.type = "number";
        add_season_input.setAttribute("min", "1");

        var add_episode_label = document.createElement("label");
        add_episode_label.setAttribute("class", "sr-only");
        add_episode_label.setAttribute("for", "episode");
        add_episode_label.innerHTML = "Episode";

        var add_episode_input = document.createElement("input");
        add_episode_input.autofocus;
        add_episode_input.setAttribute("class", "form-control");
        add_episode_input.name = "episode";
        add_episode_input.id = "episode";
        add_episode_input.placeholder = "Episode";
        add_episode_input.type = "number";
        add_episode_input.setAttribute("min", "1");

        // add the newly created tags
        upload_episode_container.appendChild(document.createElement("br"));
        upload_episode_container.appendChild(add_season_label);
        upload_episode_container.appendChild(add_season_input);
        upload_episode_container.appendChild(add_episode_label);
        upload_episode_container.appendChild(add_episode_input);
        upload_episode_container.appendChild(document.createElement("br"));
    }

    // editing existing project scenario
    if (n == 2) {

        // Container <div> where dynamic content will be placed
        var edit_episode_container = document.getElementById("edit_episode_container");

        // ensure type series
        var type = document.getElementById("change_type").value;
        var type1 = type.toLowerCase();
        var type2 = "series";
        var n = type1.localeCompare(type2)
        if (n != 0) {

            // Clear previous contents of the container
            while (edit_episode_container.hasChildNodes()) {
                edit_episode_container.removeChild(edit_episode_container.lastChild);
            }

            window.alert('Only for Series.');
            return;
        }

        // Clear previous contents of the container
        while (edit_episode_container.hasChildNodes()) {
            edit_episode_container.removeChild(edit_episode_container.lastChild);
        }

        // create a list item
        var list_item = document.createElement("li");
        list_item.setAttribute("id", "edit_episode_li");

        // Create an label and input for adding season and episode
        var add_season_label = document.createElement("label");
        add_season_label.setAttribute("class", "sr-only");
        add_season_label.setAttribute("for", "add_season");
        add_season_label.innerHTML = "Add season";

        var add_season_input = document.createElement("input");
        add_season_input.autofocus;
        add_season_input.setAttribute("class", "form-control");
        add_season_input.name = "add_season";
        add_season_input.id = "add_season";
        add_season_input.placeholder = "Add season";
        add_season_input.type = "number";
        add_season_input.setAttribute("min", "1");

        var add_episode_label = document.createElement("label");
        add_episode_label.setAttribute("class", "sr-only");
        add_episode_label.setAttribute("for", "add_episode");
        add_episode_label.innerHTML = "Add episode";

        var add_episode_input = document.createElement("input");
        add_episode_input.autofocus;
        add_episode_input.setAttribute("class", "form-control");
        add_episode_input.name = "add_episode";
        add_episode_input.id = "add_episode";
        add_episode_input.placeholder = "Add episode";
        add_episode_input.type = "number";
        add_episode_input.setAttribute("min", "1");

        // add the newly created tags
        edit_episode_container.appendChild(list_item);

        var edit_episode_li = document.getElementById("edit_episode_li");

        edit_episode_li.appendChild(add_season_label);
        edit_episode_li.appendChild(add_season_input);
        edit_episode_li.appendChild(add_episode_label);
        edit_episode_li.appendChild(add_episode_input);

    }

}


// Adding input elements dynamically to form
// https://stackoverflow.com/questions/14853779/adding-input-elements-dynamically-to-form
function addLanguages(n){

    // Number of inputs to create
    var number = document.getElementById("number_of_versions").value;

    // ensure at least two versions for new project
    if (n == 2 && number < 2) {
        window.alert('A new project has to have at least two languages.');
        return;
    }

    // ensure at least two versions for new project
    if (n == 1 && number < 1) {
        window.alert('Must add at least one language version to an existing project.');
        return;
    }

    // Container <div> where dynamic content will be placed
    var language_container = document.getElementById("language_container");

    // Clear previous contents of the container
    while (language_container.hasChildNodes()) {
        language_container.removeChild(language_container.lastChild);
    }

    // create "number" fields
    for (i = 0; i < number; i++) {

        // Create an <input> element, set its attributes
        // attributes are added differently ( dot notation, setAttr method)
        var input = document.createElement("input");
        input.autofocus;
        input.setAttribute("class", "form-control");
        input.setAttribute("list", "languages");
        input.name = "language_version" + (i + 1);
        input.id = "language_version" + (i + 1);
        input.placeholder = "Version " + (i + 1) + " (select/type)";

        // space out each language
        language_container.appendChild(document.createElement("br"));
        language_container.appendChild(input);
        addDropdownLanguages(language_container);
        language_container.appendChild(document.createElement("br"));
    }
}

// rating interface
// in mozilla the button steals all mouse events for its children
// that's why I put the event on the button itself
// https://bugzilla.mozilla.org/show_bug.cgi?id=843003
function fill(n) {
    for (i = 0; i <= n; i++) {
        var m = "star" + i.toString();
        var star = document.getElementById(m);
        star.removeAttribute("class");
        star.setAttribute("class", "fas fa-star");
        star.style.color = "gold";
    }

    for (i = (n + 1); i < 5; i++) {
        var m = "star" + i.toString();
        var star = document.getElementById(m);
        star.removeAttribute("class");
        star.removeAttribute("style");
        star.setAttribute("class", "far fa-star");
    }

    var current_star = (n + 1).toString();
    document.getElementById("current-star").innerHTML = current_star;
}

function empty() {
    for (i = 0; i < 5; i++) {
        var m = "star" + i.toString();
        var star = document.getElementById(m);
        star.removeAttribute("class");
        star.removeAttribute("style");
        star.setAttribute("class", "far fa-star");
    }

    document.getElementById("current-star").innerHTML = "";
}

// adds dropdown languages menu for different versions
function addDropdownLanguages(language_container) {

    // List of all country languages for dropdown select menu HTML FORM [closed]
    // https://stackoverflow.com/questions/38909766/list-of-all-country-languages-for-dropdown-select-menu-html-form
    var language_list = ' \
        <datalist id="languages"> \
            <option value="Afrikanns">Afrikanns</option> \
            <option value="Albanian">Albanian</option> \
            <option value="Arabic">Arabic</option> \
            <option value="Armenian">Armenian</option> \
            <option value="Basque">Basque</option> \
            <option value="Bengali">Bengali</option> \
            <option value="Bulgarian">Bulgarian</option> \
            <option value="Catalan">Catalan</option> \
            <option value="Cambodian">Cambodian</option> \
            <option value="Chinese (Mandarin)">Chinese (Mandarin)</option> \
            <option value="Croation">Croation</option> \
            <option value="Czech">Czech</option> \
            <option value="Danish">Danish</option> \
            <option value="Dutch">Dutch</option> \
            <option value="English">English</option> \
            <option value="Estonian">Estonian</option> \
            <option value="Fiji">Fiji</option> \
            <option value="Finnish">Finnish</option> \
            <option value="French">French</option> \
            <option value="Georgian">Georgian</option> \
            <option value="German">German</option> \
            <option value="Greek">Greek</option> \
            <option value="Gujarati">Gujarati</option> \
            <option value="Hebrew">Hebrew</option> \
            <option value="Hindi">Hindi</option> \
            <option value="Hungarian">Hungarian</option> \
            <option value="Icelandic">Icelandic</option> \
            <option value="Indonesian">Indonesian</option> \
            <option value="Irish">Irish</option> \
            <option value="Italian">Italian</option> \
            <option value="Japanese">Japanese</option> \
            <option value="Javanese">Javanese</option> \
            <option value="Korean">Korean</option> \
            <option value="Latin">Latin</option> \
            <option value="Latvian">Latvian</option> \
            <option value="Lithuanian">Lithuanian</option> \
            <option value="Macedonian">Macedonian</option> \
            <option value="Malay">Malay</option> \
            <option value="Malayalam">Malayalam</option> \
            <option value="Maltese">Maltese</option> \
            <option value="Maori">Maori</option> \
            <option value="Marathi">Marathi</option> \
            <option value="Mongolian">Mongolian</option> \
            <option value="Nepali">Nepali</option> \
            <option value="Norwegian">Norwegian</option> \
            <option value="Persian">Persian</option> \
            <option value="Polish">Polish</option> \
            <option value="Portuguese">Portuguese</option> \
            <option value="Punjabi">Punjabi</option> \
            <option value="Quechua">Quechua</option> \
            <option value="Romanian">Romanian</option> \
            <option value="Russian">Russian</option> \
            <option value="Samoan">Samoan</option> \
            <option value="Serbian">Serbian</option> \
            <option value="Slovak">Slovak</option> \
            <option value="Slovenian">Slovenian</option> \
            <option value="Spanish">Spanish</option> \
            <option value="Swahili">Swahili</option> \
            <option value="Swedish">Swedish </option> \
            <option value="Tamil">Tamil</option> \
            <option value="Tatar">Tatar</option> \
            <option value="Telugu">Telugu</option> \
            <option value="Thai">Thai</option> \
            <option value="Tibetan">Tibetan</option> \
            <option value="Tonga">Tonga</option> \
            <option value="Turkish">Turkish</option> \
            <option value="Ukranian">Ukranian</option> \
            <option value="Urdu">Urdu</option> \
            <option value="Uzbek">Uzbek</option> \
            <option value="Vietnamese">Vietnamese</option> \
            <option value="Welsh">Welsh</option> \
            <option value="Xhosa">Xhosa</option> \
        </datalist> \
    ';

    // add dropdown list to each language version
    language_container.insertAdjacentHTML('beforeend', language_list);
}