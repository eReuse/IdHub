const ApiError = require("./apiError")

function apiErrorHandler(err, req, res, next) {
    //conosle.err is not async --> bad for prod (use logging library like winston?)
    console.log(err)
    if (err instanceof ApiError) {
        res.status(err.code).json(err.message)
        return
    }
    res.status(500).json("unexpected API error")
}

module.exports = apiErrorHandler;