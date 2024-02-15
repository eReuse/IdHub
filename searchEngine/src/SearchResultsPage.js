import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Spinner, Accordion, ListGroup, Card } from 'react-bootstrap';
import axios from 'axios';
import { useHistory } from 'react-router-dom';


const SearchResultsPage = ({ location }) => {
    const searchQuery = new URLSearchParams(location.search).get('q');
    // const [deepSearchQuery, setDeepSearchQuery] = useState('');
    var [notFoundText, setNotFoundText] = useState('')
    var [dpps, setDpps] = useState([])
    const history = useHistory();
    var searchUrl = `http://192.168.0.211:3013/search?query=`

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



    let template
    if(notFoundText == "NOT FOUND")
        template = <h2 className="mb-4">Found 0 DPPs</h2>
    else if (dpps.length == 0){
        template = <div>
            <h2 className="mb-4">Looking for DPPs... <Spinner animation="border" /></h2>
            </div>
    }
    else{
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
