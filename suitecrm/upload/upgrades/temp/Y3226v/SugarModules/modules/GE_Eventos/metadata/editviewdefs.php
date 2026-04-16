<?php
$module_name = 'GE_Eventos';
$viewdefs [$module_name] = 
array (
  'EditView' => 
  array (
    'templateMeta' => 
    array (
      'maxColumns' => '2',
      'widths' => 
      array (
        0 => 
        array (
          'label' => '10',
          'field' => '30',
        ),
        1 => 
        array (
          'label' => '10',
          'field' => '30',
        ),
      ),
      'useTabs' => false,
      'tabDefs' => 
      array (
        'DEFAULT' => 
        array (
          'newTab' => false,
          'panelDefault' => 'expanded',
        ),
      ),
    ),
    'panels' => 
    array (
      'default' => 
      array (
        0 => 
        array (
          0 => 'name',
          1 => 'assigned_user_name',
        ),
        1 => 
        array (
          0 => 
          array (
            'name' => 'nombreevento',
            'label' => 'LBL_NOMBREEVENTO',
          ),
          1 => '',
        ),
        2 => 
        array (
          0 => 
          array (
            'name' => 'fechaevento',
            'label' => 'LBL_FECHAEVENTO',
          ),
          1 => '',
        ),
        3 => 
        array (
          0 => 
          array (
            'name' => 'presupuesto',
            'label' => 'LBL_PRESUPUESTO',
          ),
          1 => '',
        ),
        4 => 
        array (
          0 => 'description',
        ),
      ),
    ),
  ),
);
