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