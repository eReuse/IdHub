var endpoints = {}
var sections = {}
var dlts = {}
var selected_endpoint = ""
var selected_dlt = ""

document.onkeydown = function(evt) {
    evt = evt || window.event;
    //console.log(evt.key)
    // if(evt.key == "+" || evt.key == "-") change_font_size(evt.key)
    // else eel.handle_key(evt.key)
};

eel.expose(test);
function test(text) {
    // let folder = document.getElementById('input-box').value;
    // let file_div = document.getElementById('file-name');
    
    // // Call into Python so we can access the file system
    // let random_filename = await eel.pick_file(folder)();
    // file_div.innerHTML = random_filename;
    // console.log(text)

    // let div = document.getElementById('main_div');
    // div.innerHTML = text
    eel.test()
}

async function init(){
    endpoints = await eel.read_endpoints()()
    sections = await eel.read_sections()()
    dlts = await eel.read_dlts()()
    print_endpoint_selector()
}

function print_main_page() {
    // let element = document.getElementById("button");
    // element.remove();
    let body = document.getElementById("body")
    let html_content = ""
    let keys = Object.keys(sections)
    keys.forEach(elem =>{
        html_content +=`
        <button class="bar_button" onclick="load_page('${elem}')">${elem}</button>
        <div class="separator"></div>
        `
    })
    let html_text = `
    <div id="bar_div" class="left-bar">
        <div style="width:100%;height:50px;text-align: center;line-height: 50px">DEMO CLIENT</div>
        <div class="separator"></div>
        ${html_content}
        <button class="bar_button" onclick="location.reload()">Restart client</button>
        <div class="separator"></div>
    </div>
    <div id="content_div" class="right-content">
    </div>
    `;
    body.innerHTML=html_text;
}

function load_page(key){
    let div = document.getElementById("content_div")
    let html_content = ""
    sections[key].args.forEach(elem => {
        html_content += `
        <div>${elem}</div>
        <input style="margin-bottom:5px; width:50%" id="${elem}"></input><br>
        `
    })
    let html_text = `
    <div id="form_page" style="font-size:12px; width:100%;">
        <h1>${key}</h1><br>
        <div>${sections[key].description}</div><br>
        <div style="border:1px solid gray; border-radius:10px; padding:10px;">
            ${html_content}<br>
            <button onclick="process_request('${key}')">Submit</button>
        </div>
    </div> <br>
    <div id="loading_text"></div>
    `
    div.innerHTML=html_text
}

async function process_request(key){
    let div = document.getElementById("form_page")
    let args = []
    sections[key].args.forEach(elem => {
        args.push(document.getElementById(elem).value)
    })
    let loading_text = document.getElementById("loading_text")
    loading_text.innerHTML = "Processing request..."
    console.log(args)
    let result = await eel.call_api(sections[key].command, args)()
    console.log("kek")
    console.log(result)
    loading_text.innerHTML = `
    <br>
    Result
    <div style="border:1px solid gray; border-radius:10px; padding:10px; font-size:12px;">
    ${JSON.stringify(result, null, 2)}
    </div>
    `
}

// function print_init_page(){
//     let body = document.getElementById("body")
//     let html_text = `
//     <div class="init_form">
//         <button class="init_button" id="endpoint_button" onclick="print_endpoint_selector()">Select endpoint</button>
//         <button class="init_button" id="regitser_user_button" onclick="print_register_procedure()">Register user</button>
//     </div>
//     `
//     body.innerHTML=html_text;
// }


function print_endpoint_selector(){
    let body = document.getElementById("body")
    let html_content = ""
    let keys = Object.keys(endpoints)
    keys.forEach(elem => {
        console.log(endpoints[elem])
        html_content += `<button class="init_button" onclick="set_endpoint('${endpoints[elem]}')">${elem}</button>`
        console.log(html_content)
    })
    let html_text = `
    <div class="init_form">
        Select API endpoint:
        ${html_content}
    </div>
    `
    body.innerHTML=html_text;
}

function set_endpoint(endpoint){
    selected_endpoint = endpoint
    print_dlt_selector()
}

function print_dlt_selector(){
    let body = document.getElementById("body")
    let html_content = ""
    let keys = Object.keys(dlts)
    keys.forEach(elem => {
        html_content += `<button class="init_button" onclick="set_dlt('${dlts[elem]}')">${elem}</button>`
    })
    let html_text = `
    <div class="init_form">
        Select DLT:
        ${html_content}
    </div>
    `
    body.innerHTML=html_text;
}

function set_dlt(dlt){
    console.log("DLT:"+dlt)
    selected_dlt=dlt
    print_user_selector()
}

function print_user_selector(){
    let body = document.getElementById("body")
    let html_text = `
    <div class="init_form">
        Input API key:
        <input id="api_key"></input>
        <button class="init_button" onclick="set_api_object(document.getElementById('api_key').value)">Submit</button>
        or
        <button class="init_button" onclick="print_user_registration()">Register new user</button>
    </div>
    `
    body.innerHTML=html_text;

}

function set_api_object(key){
    eel.init_api_object(selected_endpoint,key,selected_dlt)
    print_main_page()
}

async function print_user_registration(){
    user_key = await eel.register_new_user(selected_endpoint)()
    let body = document.getElementById("body")
    let html_text = `
    <div class="init_form">
        New user's API key: <div style="font-size:12px;">${user_key}</div>
        <button class="init_button" style="width:350px;" onclick="set_api_object('${user_key}')">Continue with this key</button>
    </div>
    `
    body.innerHTML=html_text;

}