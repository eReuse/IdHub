import React, { useState, useEffect, Fragment } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Accordion, ListGroup, Spinner, ListGroupItem } from 'react-bootstrap';
import axios from 'axios';

const TrustActor = (props) => {
    const [template, setTemplate] = useState("")
    const [verifyPressed, setVerifyPressed] = useState(0)
    const [parentCredential, setParentCredential] = useState("")
    const root="0x2f67B1d86651aF2E37E39b30F2E689Aa7fbAc79F"

    const press = (turn) => {
	console.log("SOY TRUSTACTOR: " + JSON.stringify(props))
        if (turn == 1) {
            setVerifyPressed(verifyPressed + 1)
            axios.post(`${props.apiUrl}/getCredentials`,
                {
                    CredentialType: props.type,
                    target_user: props.address
                },
                {
                    headers: {
                        dlt: "ethereum"
                    }
                }).then((data) => {
                    console.log(data)
                    if(data.data.data[0]==root){
                        setParentCredential(
                            <ListGroup>
                <TrustActor type="Root" address={data.data.data[0]} key_for_event={props.key_for_event+props.address+data.data.data[0]} apiUrl={props.apiUrl}></TrustActor>
            </ListGroup>
                        )
                    }
                    else if(data.data.data[1]){
                        setParentCredential(
                        <TrustActor type="Issuer" address={data.data.data[0]} key_for_event={props.key_for_event+props.address+data.data.data[0]} apiUrl={props.apiUrl}></TrustActor>
                        )
                    }

                    press(2)
                }).catch((error) => {
                    press(3)
                })
        }
        else if (turn == 2) setVerifyPressed(2)
        else setVerifyPressed(3)
    }

    useEffect(() =>{
        // var actualDate = new Date(props.proof.timestamp * 1000)
        // setDate(actualDate)
        // console.log(verifyPressed)
        if(props.type == "Root"){
            setTemplate(
                <ListGroup>
                <ListGroupItem>{root}<br></br>Credential type: {"Root"}</ListGroupItem>
            </ListGroup>
            )
        }
        else if(verifyPressed == 0){
            setTemplate(
            <ListGroup>
                <ListGroupItem>{props.address}<button onClick={() => press(1)} style={{float:'right'}}>Verify</button><br></br>Credential type: {props.type}</ListGroupItem>
            </ListGroup>
            )
        }
        else if (verifyPressed == 1){
            setTemplate(
                <ListGroup>
                    <ListGroupItem>{props.address}<Spinner style={{float:'right'}} animation="border" /><br></br>Credential type: {props.type}</ListGroupItem>
                </ListGroup>
                )
        }
        else if (verifyPressed == 2){
            setTemplate(
                <Accordion.Item eventKey={props.key_for_event}>
                    <Accordion.Header><div>{props.address}<span style={{float:'right'}}>✅</span><br></br>Credential type: {props.type}</div></Accordion.Header>
                    <Accordion.Body>{parentCredential}</Accordion.Body>
                </Accordion.Item>
                )
        }
        else{
            setTemplate(
                <ListGroup>
                    <ListGroupItem>{props.address}<span style={{float:'right'}}>❌</span><br></br>Credential type: {props.type}</ListGroupItem>
                </ListGroup>
                )
        }
        //setVerifyPressed(0)
    }, [verifyPressed])

    
    

    return(<div>
        {/* {template} */}
            {template}
    </div>
        
    )
}

export default TrustActor;
