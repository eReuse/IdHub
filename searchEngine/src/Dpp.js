import React, { useState, useEffect, Fragment } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Accordion, ListGroup } from 'react-bootstrap';
import axios from 'axios';
import Proof from './Proof';

const Dpp = (props) => {
    var completeUrl=props.url+props.chid+":"+props.dpp
    var [deviceInfo, setDeviceInfo] = useState("")
    var [components, setComponents] = useState([])
    var [componentsCHID, setComponentsCHID] = useState([])
    var [proofs, setProofs] = useState([])

    var apiUrl = process.env.REACT_APP_CONNECTOR_API
    var apiKey = process.env.REACT_APP_CONNECTOR_API_TOKEN
    const headers = { 'Accept': 'application/json' };

    useEffect(() => {
        axios.get(completeUrl, { headers })
        .then((response)=>{
            console.log(response)
            setDeviceInfo(response.data.data.device)
            setComponents(response.data.data.components)
            setComponentsCHID(response.data.data.components)
        })
    }, [])

    useEffect(() =>{
        var proofsArray=[]
        axios.post(`${apiUrl}/getProofs`, 
        {
            api_token: apiKey,
            DeviceCHID: props.chid
        },
        {
            headers:{
                dlt: "ethereum"
            }
        }).then((data)=>{
            console.log(data)
            data.data.data.forEach((element) =>{
                if(element.phid == props.dpp)
                    proofsArray.push(element)
            })
            console.log(proofsArray)
            setProofs(proofsArray)
        })
        // componentsCHID.forEach((component) => {
        //     proofsArray.push({doc_hash: "exampleHash", hash_algorithm: "exampleAlgorithm"})
        // })
        // setProofs(proofsArray)
    }, [componentsCHID])

    var info = []
    for (var key in deviceInfo){
        info.push(<ListGroup.Item>{key}: {deviceInfo[key]}</ListGroup.Item>)
    }
    
    const drawComponentInfo = (component)=> {
        var retArray = []
        for (var key in component){
            retArray.push(<ListGroup.Item>{key}: {component[key]}</ListGroup.Item>)
        }
        return retArray
    }



    return(
        <Accordion.Item eventKey={props.dpp}>
            <Accordion.Header>{props.dpp}</Accordion.Header>
            <Accordion.Body>
                <Tabs
                    defaultActiveKey="info"
                    className='mb-3'
                >
                    <Tab eventKey="info" title="Info">
                        <ListGroup>{info}</ListGroup><br></br>
                        <a href={completeUrl}>Link to inventory DPP</a>
                    </Tab>
                    <Tab eventKey="components" title="Components">
                        <Accordion alwaysOpen>
                            {components.map((component)=>(
                                <Accordion.Item eventKey={component.serialNumber+component.model+component.manufacturer}>
                                    <Accordion.Header>{component.type}</Accordion.Header>
                                    <Accordion.Body><ListGroup>
                                    {drawComponentInfo(component)}
                                        </ListGroup></Accordion.Body>
                                </Accordion.Item>
                            ))}
                        </Accordion>
                    </Tab>
                    <Tab eventKey="proofs" title="Proofs">
                    <ListGroup>{
                    proofs.map((proof) => (
                        <ListGroup.Item>
                            {/* <div>Document hash: {proof.doc_hash}<button style={{float:'right'}}>Verify</button></div>
                            Hash algorithm: {proof.hash_algorithm} */}
                            <Proof proof={proof} apiUrl={apiUrl} dpp={props.dpp}></Proof>
                        </ListGroup.Item>
                    ))
                    }</ListGroup>
                    </Tab>
                </Tabs>
            </Accordion.Body>
        </Accordion.Item>
    )
}

export default Dpp;
