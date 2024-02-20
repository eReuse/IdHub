import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Spinner, Accordion } from 'react-bootstrap';
import axios from 'axios';
import Dpp from './Dpp';


const SearchResultsPageDeep = ({ location }) => {
    const searchQuery = new URLSearchParams(location.search).get('q');
    var [notFoundText, setNotFoundText] = useState('')
    var [invUrl, setInvUrl] = useState('')
    var [dpps, setDpps] = useState([])
    var resolverUrl = `${process.env.REACT_APP_EREUSE_DID_RESOLVER}/did:ereuse:`
    var idIndexUrl = `${process.env.REACT_APP_ID_INDEX_API}/getURL?id=`
    var chid = searchQuery.split(":")[0]

    useEffect(() => {
        // Implement your search results logic here using the searchQuery
        console.log('Search query:', searchQuery);
        var didDocUrl = resolverUrl + chid
        axios.get(didDocUrl, { timeout: 2000 })
            .then(data => {
                let service
                if (data.data.didDocument == null)
                    setNotFoundText("NOT FOUND")
                else {
                    data.data.didDocument.service.forEach(element => {
                        if (element.type == "DeviceHub")
                            service = element
                    });
                    let inventoryUrl = idIndexUrl + service.serviceEndpoint
                    console.log(inventoryUrl)
                    axios.get(inventoryUrl)
                        .then(response => {
                            console.log(response.data.url + "/did/" + chid)
                            setInvUrl(`${response.data.url + "/did/"}`)
                            axios.get(`${response.data.url + "/did/" + searchQuery}`)
                                .then(deviceData => {
                                    console.log(deviceData)
                                    // console.log(deviceData.data.data.components)
                                    console.log(JSON.parse(deviceData.data.data[0].document))
                                    var dppsArray = deviceData.data.data
                                    // dppsArray.push(deviceData.data.data[0])
                                    setDpps(dppsArray)
                                    console.log(dpps)
                                    // setDidDoc(JSON.stringify(deviceData.data))
                                })
                            // setDidDoc(`${response.data.url + "/did/" + searchQuery}`)
                        })
                }
                // setDidDoc(JSON.stringify(data.data))
            })
        .catch(error => {
            if (error.code === 'ECONNABORTED') {
              console.log('Request timed out');
            } else {
              console.log(error.message);
            }
          })
    }, []);

    let template
    if(notFoundText == "NOT FOUND")
        template = <h2 className="mb-4">NOT FOUND</h2>
    else if (dpps.length == 0){
        template = <div>
            <h2 className="mb-4">Looking for DPPs... <Spinner animation="border" /></h2>
            </div>
    }
    else{
        template = <div>
            <Accordion alwaysOpen>
        {dpps.map((item) => (
            <Dpp dpp={item.dpp.split(":")[1]} url={invUrl} chid={chid}>item.dpp</Dpp>
        ))}
    </Accordion>
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

export default SearchResultsPageDeep;
