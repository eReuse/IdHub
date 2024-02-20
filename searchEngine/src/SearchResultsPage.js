import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Spinner, Accordion, ListGroup, Card } from 'react-bootstrap';
import axios from 'axios';
import { useHistory } from 'react-router-dom';
import reward from './reward.png'


const SearchResultsPage = ({ location }) => {
    const searchQuery = new URLSearchParams(location.search).get('q');
    // const [deepSearchQuery, setDeepSearchQuery] = useState('');
    var [notFoundText, setNotFoundText] = useState('')
    var [temp1_dpps, setTemp1] = useState([])
    var [temp2_dpps, setTemp2] = useState([])
    var [dpps, setDpps] = useState([])
    const history = useHistory();
    var ERC20Url = process.env.REACT_APP_CONNECTOR_API+"/balanceOf?chid="
    var searchUrl = process.env.REACT_APP_DPP_INDEXER+`/search?query=`
    var iotaEndpoint = process.env.REACT_APP_IOTA_API+'/api/dpp-registry/v1/'
    var iotaToken = process.env.REACT_APP_IOTA_TOKEN

    useEffect(() => {
        console.log("FIRST EFFECT")
        // Implement your search results logic here using the searchQuery
        // console.log('Search query:', searchQuery);

        axios.get(encodeURI(searchUrl + searchQuery))
            .then(data => {
                console.log("YYYY")
                var dppsArray = data.data.result
                console.log(dppsArray.length)
                if (dppsArray.length == 0) setNotFoundText("NOT FOUND")
                setDpps(dppsArray)
                setTemp1(dppsArray)
            })
            .catch(error => {
                if (error.code === 'ECONNABORTED') {
                    console.log('Request timed out');
                } else {
                    console.log(error.message);
                }
            })
    }, []);

    useEffect(() => {
        console.log("SECOND EFFECT")
        const execute = async () => {
            let dppsArray = temp1_dpps
            // IOTA STATUS
            for (let i = 0; i < dppsArray.length; i++) {
                try {
                    let result2 = await axios.get(encodeURI(iotaEndpoint + `registrations?dppRealProductID=${dppsArray[i].item.chid}`), {
                        headers: {
                            "Authorization": iotaToken
                        }
                    })
                    let outputId = result2.data.items[0]
                    let result3 = await axios.get(encodeURI(iotaEndpoint + `registration/id/${outputId}`), {
                        headers: {
                            "Authorization": iotaToken
                        }
                    })
                    let aliasId = result3.data.aliasId
                    let result4 = await axios.get(encodeURI(iotaEndpoint + `registration/status/${aliasId}`), {
                        headers: {
                            "Authorization": iotaToken
                        }
                    })
                    dppsArray[i].item.iotaStatus = "YES"
                } catch (error) {
                    dppsArray[i].item.iotaStatus = "NO"
                }
            }
            // ERC20 STATUS
            // for (let i = 0; i < dppsArray.length; i++) {
            //     let result2 = await axios.get(encodeURI(ERC20Url+dppsArray[i].item.chid))
            //     dppsArray[i].item.balance=result2.data.balance
            // }
            setTemp2(dppsArray)
        }

        execute()
    }, [temp1_dpps]);

    useEffect(() => {
        console.log("THIRD EFFECT")
        const execute = async () => {
            let dppsArray = temp2_dpps
            for (let i = 0; i < dppsArray.length; i++) {
                let result2 = await axios.get(encodeURI(ERC20Url + dppsArray[i].item.chid))
                dppsArray[i].item.balance = result2.data.balance
            }
            setDpps(dppsArray)
        }
        execute()
    }, [temp2_dpps]);

    const handleSearch = (e, query) => {
        e.preventDefault();
        // Implement your search logic here
        // For simplicity, we will just navigate to the search results page with the query as a parameter
        history.push(`/deepSearch?q=${query}`);
    };

    const spinnerDraw = (spin, thing, which) => {
        if (spin) {
            if (which == "iota") return <div style={{
                height: "50px",
                width: "180px",
                border: "2px solid gray",
                backgroundColor: "#d3d3d3",
                borderRadius: "5px",
                display: "inline-block",
                position: "relative",
                marginRight: "30px",
                marginTop:"8px"

            }}><span
                style={{
                    position: "absolute",
                    float: "left",
                    left: "10px",
                    top: "15px",
                    fontSize: "15px"
                }}>
                    Checking DPP...
                </span>
                <div style={{
                    position: "absolute",
                    width: "47px",
                    height: "47px",
                    border: "3px solid black",
                    backgroundColor: "gray",
                    borderRadius: "50%",
                    marginLeft: "150px"
                }}>
                    <span style={{
                        position: "relative",
                        float: "left",
                        left: "5px",
                        top: "0px",
                        fontSize: "35px",
                        color:"white"
                    }}>
                        <Spinner style={{color:"white", fontSize:"20px"}} animation="border" />
                    </span>
                </div>
            </div>
            return <Spinner style={{marginRight:"15px", marginTop:"100px"}} animation="border" />
        }
        if (which == "erc" && thing > 0) return <img style={{marginRight:"15px", marginTop:"80px"}} src={reward} width={60} />
        if (which == "iota") {
            if (thing == "YES") return <div style={{
                height: "50px",
                width: "180px",
                border: "2px solid gray",
                backgroundColor: "#ebf1e7",
                borderRadius: "5px",
                display: "inline-block",
                position: "relative",
                marginRight: "30px",
                marginTop:"8px"

            }}><span
                style={{
                    position: "absolute",
                    float: "left",
                    left: "10px",
                    top: "15px",
                    fontSize: "15px"
                }}>
                    Registered DPP
                </span>
                <div style={{
                    position: "absolute",
                    width: "47px",
                    height: "47px",
                    border: "3px solid black",
                    backgroundColor: "green",
                    borderRadius: "50%",
                    marginLeft: "150px"
                }}>
                    <span style={{
                        position: "relative",
                        float: "left",
                        left: "7px",
                        top: "0px",
                        fontSize: "35px",
                        color:"white"
                    }}>✓</span>
                </div>
            </div>
            else{ return <div style={{
                height: "50px",
                width: "180px",
                border: "2px solid gray",
                backgroundColor: "#f9e9e9",
                borderRadius: "5px",
                display: "inline-block",
                position: "relative",
                marginRight: "30px",
                marginTop:"8px"

            }}><span
                style={{
                    position: "absolute",
                    float: "left",
                    left: "10px",
                    top: "15px",
                    fontSize: "15px"
                }}>
                    Unregistered DPP
                </span>
                <div style={{
                    position: "absolute",
                    width: "47px",
                    height: "47px",
                    border: "3px solid black",
                    backgroundColor: "red",
                    borderRadius: "50%",
                    marginLeft: "150px"
                }}>
                    <span style={{
                        position: "relative",
                        float: "left",
                        left: "12px",
                        top: "3px",
                        fontSize: "30px",
                        color:"white"
                    }}>X</span>
                </div>
            </div>
        }
    }}

    const templateDraw = (iotaspin, ercspin) => {
        return <div>
            <h2 className="mb-4">Found {dpps.length} DPPs:</h2>
            <ListGroup>
                {dpps.map((elem) => (
                    <ListGroup.Item>
                        <Card>
                            <Card.Title>
                                <a style={{ display: "inline-block", marginRight: "20px" }} onClick={(e) => handleSearch(e, elem.item.chid)} href="#">{elem.item.manufacturer + " "}{elem.item.model}</a>
                                <span style={{ display: "inline-block", float: "right" }}>{spinnerDraw(iotaspin, elem.item.iotaStatus, "iota")}</span>
                            </Card.Title>
                            <Card.Text>
                                <span style={{ display: "inline-block", marginRight: "20px" , marginTop:"-20px"}}>
                                    Chassis: {elem.item.chassis}<br></br>
                                    Manufacturer: {elem.item.manufacturer}<br></br>
                                    Model: {elem.item.model}<br></br>
                                    SKU: {elem.item.sku}<br></br>
                                    Serial number: {elem.item.serialNumber}<br></br>
                                    CHID: {elem.item.chid}<br></br>
                                    PHID: {elem.item.phid}<br></br>
                                </span>
                                <span style={{ display: "inline-block", float: "right" }}>
                                    {spinnerDraw(ercspin, elem.item.balance, "erc")}<br></br>
                                </span>
                            </Card.Text>
                        </Card>
                    </ListGroup.Item>
                ))}
            </ListGroup>
        </div>
    }


    let template
    if (notFoundText == "NOT FOUND")
        template = <h2 className="mb-4">Found 0 DPPs.</h2>
    else if (dpps.length == 0) {
        template = <div>
            <h2 className="mb-4">Looking for DPPs... <Spinner animation="border" /></h2>
        </div>
    }
    else if (temp1_dpps[0].item.iotaStatus == undefined) {
        template = templateDraw(true, true)
    }
    // const drawShit = () => {
    //     var retVal
    //     dpps.forEach(element => {
    //         // retVal += <div>{element.dpp}</div>
    //         return <h1>element.dpp</h1>
    //     })
    //     return retVal
    // }
    else if (temp2_dpps[0].item.balance == undefined) {
        template = templateDraw(false, true)
    }
    else {
        template = templateDraw(false, false)
    }

    return (
        <Container className="mt-5">
            <Row className="justify-content-center">
                <Col md={8}>
                    {/* <Accordion>
                        {dpps.map((item) => (
                            <Dpp dpp={item.dpp}>item.dpp</Dpp>
                        ))}
                    </Accordion> */ template}

                </Col>
            </Row>
        </Container>
    );
};

export default SearchResultsPage;
