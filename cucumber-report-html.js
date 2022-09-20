var reporter = require('cucumber-html-reporter');

var options = {
        theme: 'bootstrap',
        jsonFile: './features/reports/cucumber_report.json',
        output: './features/reports/cucumber_report.html',
        reportSuiteAsScenarios: true,
        scenarioTimestamp: true,
        launchReport: true,
        metadata: {
            "App Version":"2.0.0",
            "Test Environment": "STAGING",
            "Browser": "Chrome  54.0.2840.98",
            "Executed": "Remote"
        }
    };

    reporter.generate(options);
    

    //more info on `metadata` is available in `options` section below.

    //to generate consodilated report from multi-cucumber JSON files, please use `jsonDir` option instead of `jsonFile`. More info is available in `options` section below.