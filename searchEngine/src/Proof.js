import React, { useState, useEffect, Fragment } from 'react';
import { Container, Row, Col, Form, Button, Tabs, Tab, Accordion, ListGroup, Spinner } from 'react-bootstrap';
import axios from 'axios';
import TrustActor from './TrustActor';

const Proof = (props) => {
    const [template, setTemplate] = useState("")
    const [verifyPressed, setVerifyPressed] = useState(0)
    const [datet, setDate] = useState(new Date(props.proof.timestamp*1000))
    const [test, setTest] = useState(false)

    const press = (turn) =>{
        if(turn==1){
            setVerifyPressed(verifyPressed+1)
            

            console.log(props.proof)

            axios.post(`${props.apiUrl}/verifyProof`, 
        {
            DeviceCHID: props.chid,
            InventoryID: props.proof.InventoryID,
            Timestamp: props.proof.timestamp,
            DocumentHash: props.proof.DocumentHash
        },
        {
            headers:{
                dlt: "ethereum"
            }
        }).then((data)=>{
            console.log(data)
            if(data.data.data == true)
                setTest(true)
                setTimeout(()=>press(2), 1000)
            // data.data.data.forEach((element) =>{
            //     proofsArray.push(element)
            // })
            // console.log(proofsArray)
            // setProofs(proofsArray)
        })
        }
        else setVerifyPressed(2)
    }

    useEffect(() =>{
        // var actualDate = new Date(props.proof.timestamp * 1000)
        // setDate(actualDate)
        // console.log(verifyPressed)
        if(props.proof.Type == "Funds_released"){
            setTemplate(<div style={{width:"100%"}}>
                <div style={{display: "inline-block"}}>
                Proof type: {props.proof.Type}
                </div>
                </div>)
        }
        else if(verifyPressed == 0){
            console.log("TURN 0")
            setTemplate(<div style={{width:"100%"}}>
                <div style={{display: "inline-block"}}>
                Proof type: {props.proof.Type}
                </div>
                <button onClick={() => press(1)} style={{display: "inline-block",position:"relative",float:'right', marginRight:"10px"}}>
                Verify
                </button>
                </div>)
        }
        else if (verifyPressed == 1){
            console.log("TURN 1")
            setTemplate(<div style={{width:"100%"}}>
                <div style={{display: "inline-block"}}>
                Proof type: {props.proof.Type}
                </div>
                <Spinner style={{display: "inline-block",position:"relative",float:'right', marginRight:"10px", fontSize:"10px"}} animation="border" />
                </div>)
        }
        else{
            console.log("TURN 2")
            if(test)
                setTemplate(<div style={{width:"100%"}}>
                    <div style={{display: "inline-block"}}>
                    Proof type: {props.proof.Type}
                    </div>
                    <span style={{display: "inline-block",position:"relative",float:'right', marginRight:"10px"}}>
                    ✅
                    </span>
                    </div>)
            else
                setTemplate(<div style={{width:"100%"}}>
                    <div style={{display: "inline-block"}}>
                    Proof type: {props.proof.Type}
                    </div>
                    <span style={{display: "inline-block",position:"relative",float:'right', marginRight:"10px"}}>
                    ❌
                    </span>
                    </div>)
        }
        //setVerifyPressed(0)
    }, [verifyPressed])

    const proofType = (type) => {
        if(type == "Funds_released") return "verifier"
        return "operator"
    }
    

    return(<div>
        {/* {template} */}

        <Accordion.Item eventKey={template+props.proof.DocumentHash+props.proof.timestamp+props.dpp}>
            <Accordion.Header>{template}</Accordion.Header>
            <Accordion.Body>
            <ListGroup>
            <ListGroup.Item>Creator: {props.proof.IssuerID}</ListGroup.Item>
            <ListGroup.Item>Document hash: {props.proof.DocumentHash}</ListGroup.Item>
            <ListGroup.Item>Hash algorithm: {props.proof.DocumentHashAlgorithm}</ListGroup.Item>
            <ListGroup.Item>Inventory ID: {props.proof.InventoryID}</ListGroup.Item>
            <ListGroup.Item>Date: {datet.toString()}</ListGroup.Item>
            <ListGroup.Item>Block: {props.proof.blockNumber}</ListGroup.Item>
            {/* <ListGroup.Item>
                <Accordion.Item eventKey={props.proof.IssuerID+props.proof.DocumentHash+props.proof.timestamp}>
                    <Accordion.Header>Trust chain</Accordion.Header>
                    <Accordion.Body><TrustActor type={proofType(props.proof.Type)} address={props.proof.IssuerID} key_for_event={props.proof.IssuerID+props.proof.timestamp} apiUrl={props.apiUrl}></TrustActor></Accordion.Body>
                </Accordion.Item>
            </ListGroup.Item> */}
            </ListGroup>
            </Accordion.Body>
        </Accordion.Item>
    </div>
        
    )
}

export default Proof;