<?php

namespace dataConnector;

class Connector
{
  private static $_api = "https://instant-data-visualiser.appspot.com/api/v1/";
  //private static $_api = "http://localhost:8080/api/v1/";
  private $_appName = "";
  private $_token = "";

  function __construct($token, $appName){
    $this->_token = $token;
    $this->_appName = $appName;
  }

  function getAppName(){
    return $this->_appName;
  }

  function setAppName($value){
    $this->_appName = $value;
  }

  function getToken(){
    return $this->_token;
  }

  function setToken($value){
    $this->_token = $value;
  }

  function postData($data){
    $dataPacket = array();
    foreach($data as $key => $value){
      $dataPacket[] = array("kind"=>$key, "value"=>$value);
    }

    $data_string = json_encode($dataPacket);  
    $url = self::$_api . $this->_appName . "/data/";

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL,$url);
    curl_setopt($ch, CURLOPT_POST, true); 
    curl_setopt($ch, CURLOPT_POSTFIELDS, "data=$data_string&token=$this->_token");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

    $result = curl_exec($ch);
    curl_close($ch);

    return $result;
  }
}
