import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Spinner, Accordion, ListGroup, Card } from 'react-bootstrap';
import axios from 'axios';
import { useHistory } from 'react-router-dom';
import reward from './reward.png'
import reward_spent from './reward_spent.png'


const SearchResultsPage = ({ location }) => {
    const searchQuery = new URLSearchParams(location.search).get('q');
    // const [deepSearchQuery, setDeepSearchQuery] = useState('');
    var [notFoundText, setNotFoundText] = useState('')
    var [temp1_dpps, setTemp1] = useState([])
    var [dpps, setDpps] = useState([])
    const history = useHistory();
    var ERC20Url = process.env.REACT_APP_CONNECTOR_API+"/balanceOf?chid="
    var searchUrl = process.env.REACT_APP_DPP_INDEXER+`/search?query=`

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
            for (let i = 0; i < dppsArray.length; i++) {
                let result2 = await axios.get(encodeURI(ERC20Url + dppsArray[i].item.chid))
                dppsArray[i].item.balance = result2.data.balance
                dppsArray[i].item.address = result2.data.address
            }
            setDpps(dppsArray)
        }
        execute()
    }, [temp1_dpps]);

    const handleSearch = (e, query) => {
        e.preventDefault();
        // Implement your search logic here
        // For simplicity, we will just navigate to the search results page with the query as a parameter
        history.push(`/deepSearch?q=${query}`);
    };

    const spinnerDraw = (spin, thing, which, output) => {
        // if (which == "erc" && thing > 0) return <img style={{marginRight:"15px", marginTop:"80px"}} src={reward} width={60} />
        if (which == "erc" && thing > 0) return <div style={{marginRight:"15px", marginTop:"60px"}}>
        <img src={reward} width={60} /><br></br>
        <div style={{width:"100%", textAlign:"center"}}>{thing}</div></div>
        else if (which == "erc" && thing == 0) return <div style={{marginRight:"15px", marginTop:"60px"}}>
        <img src={reward_spent} width={60} /><br></br>
        <div style={{width:"100%", textAlign:"center"}}>{thing}</div></div>
        }

    const templateDraw = (iotaspin, ercspin) => {
        return <div>
            <h2 className="mb-4">Found {dpps.length} DPPs:</h2>
            <ListGroup>
                {dpps.map((elem) => (
                    <ListGroup.Item>
                        <Card>
                            <Card.Title>
                                <a style={{ display: "inline-block", marginRight: "20px" }} onClick={(e) => handleSearch(e, elem.item.chid)} href="#">{elem.item.manufacturer + " "}{elem.item.model}</a>
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
                                    {spinnerDraw(ercspin, elem.item.balance, "erc",elem.item.address)}<br></br>
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
