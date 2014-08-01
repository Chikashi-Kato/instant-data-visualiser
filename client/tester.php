<?php
require_once("data-connector.php");

$connector = new dataConnector\Connector("a2e56490621ef21bf22f168673962c807a30b4b62eb16f7d983e1500df5e3734", "test");
$data = array("length"=>rand(0, 1000), "processes"=>rand(0,12));
$connector->postData($data);
