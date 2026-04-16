<?php
$module_name = 'GE_Eventos';
$listViewDefs [$module_name] = 
array (
  'NAME' => 
  array (
    'width' => '32%',
    'label' => 'LBL_NAME',
    'default' => true,
    'link' => true,
  ),
  'ASSIGNED_USER_NAME' => 
  array (
    'width' => '9%',
    'label' => 'LBL_ASSIGNED_TO_NAME',
    'module' => 'Employees',
    'id' => 'ASSIGNED_USER_ID',
    'default' => true,
  ),
  'NOMBREEVENTO' => 
  array (
    'type' => 'varchar',
    'label' => 'LBL_NOMBREEVENTO',
    'width' => '10%',
    'default' => true,
  ),
  'FECHAEVENTO' => 
  array (
    'type' => 'date',
    'label' => 'LBL_FECHAEVENTO',
    'width' => '10%',
    'default' => true,
  ),
  'PRESUPUESTO' => 
  array (
    'type' => 'currency',
    'label' => 'LBL_PRESUPUESTO',
    'currency_format' => true,
    'width' => '10%',
    'default' => true,
  ),
);
