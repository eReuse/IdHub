import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Spinner, Accordion, ListGroup, Card } from 'react-bootstrap';
import axios from 'axios';
import { useHistory } from 'react-router-dom';
import { forEach } from 'node-persist';


const SearchResultsPage = ({ location }) => {
    const searchQuery = new URLSearchParams(location.search).get('q');
    // const [deepSearchQuery, setDeepSearchQuery] = useState('');
    var [notFoundText, setNotFoundText] = useState('')
    var [dpps, setDpps] = useState([])
    const history = useHistory();
    var searchUrl = `http://dpp_indexer:304/search?query=`
    var iotaEndpoint = 'https://api.stable.iota-ec.net/api/dpp-registry/v1/'
    var iotaToken = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJpb3RhIiwic3ViIjoiaW90YSIsImF1ZCI6WyJpb3RhIl0sIm5iZiI6MTY4ODU1MjY2MCwiaWF0IjoxNjg4NTUyNjYwLCJqdGkiOiIxNjg4NTUyNjYwIn0.F3FRT_Nn-s7rZqQHJc5Bk8T7fKhGB0ifpEOEnj3TysQ'

    useEffect(() => {
        // Implement your search results logic here using the searchQuery
        console.log('Search query:', searchQuery);

        axios.get(encodeURI(searchUrl + searchQuery))
            .then(data => {
                var dppsArray = data.data.result
                if (dppsArray.length == 0) setNotFoundText("NOT FOUND")
                setDpps(dppsArray)
            })
            .catch(error => {
                if (error.code === 'ECONNABORTED') {
                    console.log('Request timed out');
                } else {
                    console.log(error.message);
                }
            })
    }, []);

    const handleSearch = (e, query) => {
        e.preventDefault();
        // Implement your search logic here
        // For simplicity, we will just navigate to the search results page with the query as a parameter
        history.push(`/deepSearch?q=${query}`);
    };

    // const printExtraInfo = (chid) => {
    //     var iota_text = ""
    //     //IOTA registry
    //     try {
    //         axios.get(encodeURI(iotaEndpoint + `registrations?dppRealProductID=${chid}`), {
    //             headers: {
    //                 "Authorization": iotaToken
    //             }
    //         }).then(data1 => {
    //             console.log("SHEESH")
    //             iota_text = data1.data.items[0]
    //             console.log(data1.data.items[0])
    //         })
    //     }catch(error){
    //         console.log("ERRORRRRR")
    //     }
    //     //ERC20
    //     return iota_text
    // }



    let template
    if(notFoundText == "NOT FOUND")
        template = <h2 className="mb-4">Found 0 DPPs</h2>
    else if (dpps.length == 0){
        template = <div>
            <h2 className="mb-4">Looking for DPPs... <Spinner animation="border" /></h2>
            </div>
    }
    else {
        var device_status = {}
        dpps.forEach((element) => {
            //IOTA registry
            try {
                axios.get(encodeURI(iotaEndpoint + `registrations?dppRealProductID=${element.item.chid}`), {
                    headers: {
                        "Authorization": iotaToken
                    }
                }).then(data1 => {
                    var outputId = data1.data.items[0]
                    axios.get(encodeURI(iotaEndpoint + `registration/id/${outputId}`), {
                        headers: {
                            "Authorization": iotaToken
                        }
                    }).then(data2 => {
                        var aliasId = data2.data.aliasId
                        axios.get(encodeURI(iotaEndpoint + `registration/status/${aliasId}`), {
                            headers: {
                                "Authorization": iotaToken
                            }
                        }).then(data3 => {
                            device_status[element.item.chid] = {
                                status: "kek"
                            }
                        })
                    })
                })
            } catch (error) {
                console.log("ERRORRRRR")
            }
            //ERC20
        })
        template = <div>
            <h2 className="mb-4">Found {dpps.length} DPPs:</h2>
            <ListGroup>
        {dpps.map((elem) => (
            <ListGroup.Item>
                <Card>
                    <Card.Title><a onClick={(e) => handleSearch(e, elem.item.chid)} href="#">{elem.item.manufacturer + " "}{elem.item.model}</a></Card.Title>
                    <Card.Text>
                        Chassis: {elem.item.chassis}<br></br>
                        Manufacturer: {elem.item.manufacturer}<br></br>
                        Model: {elem.item.model}<br></br>
                        SKU: {elem.item.sku}<br></br>
                        Serial number: {elem.item.serialNumber}<br></br>
                        CHID: {elem.item.chid}<br></br>
                        PHID: {elem.item.phid}<br></br>
                        {/* SOME: {device_status[elem.item.chid].status} */}
                    </Card.Text>
                </Card>
            </ListGroup.Item>
        ))}
    </ListGroup>
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
