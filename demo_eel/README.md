# Demo client

Demo client made with eel. Using the ereuseapi lib. Launches a webserver on port 8000 per default (-p flag to change it) and opens a chrome instance to the server. If chrome is not available, another browser can be specified with the -m flag. The -m flag set to "None" tells the app to not open a browser instance. The webserver can still be accessed through any other web browser.

## Dependencies

```
pip install --index-url https://test.pypi.org/simple/ ereuseapitest
pip install eel
```

## Usage
Options:
```
 -m browser (browser options: chrome, electron, edge, None) (Any other string will open the default system browser.)
 -p port
 ```
