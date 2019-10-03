<?php 
	# Get the start time when the http test starts
	error_reporting(E_ALL);
	$file = "/var/www/html/http_test/test.txt";
	$file = escapeshellarg($file);
	$line = `tail -n 2 $file`;

	$phpfile = fopen("/var/www/html/http_test/php.txt", "w+") or die("Unable to open file!");
	fwrite($phpfile, $line);
	fclose($phpfile);
?> 
