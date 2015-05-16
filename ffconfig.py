#
# configuration for flowfall
#

ofswitches = [
    {
        "dpid" : 1,
        "servicebit" : 3,
        "vlan" : {
            115 : {
                "vnf_up_ports" : [
                    {
                        "port_num" : 49, "tagged" : False,
                        "mac" : [ "02:00:ff:02:00:00" ]
                        },
                    ],

                "vnf_down_ports" : [],

                "non_up_ports" :
                [ { "port_num" : 50, "tagged" : True,
                    "mac" : [ None ] }, ],

                "non_down_ports" :
                [ { "port_num" : 51, "tagged" : True,
                    "mac" : [ "52:54:00:2e:ba:a5" ] }, ],

                },
            }
        },
    {
        "dpid" : 2,
        "servicebit" : False,
        "vlan" : {
            115 : {

                "vnf_up_ports" : [],

                "vnf_down_ports" : [
                    {
                        "port_num" : 66, "tagged" : False,
                        "mac" : [ "02:00:ee:02:00:00" ]
                        },
                    ],

                "non_up_ports" :
                    [ { "port_num" : 68, "tagged" : True,
                        "mac" : [ "90:e2:ba:3a:2f:90" ] }, ],

                "non_down_ports" :
                    [ { "port_num" : 67, "tagged" : True,
                        "mac" : [ None ] }, ],

                },
            }
        }
    ]



prefixes = [
    { "prefix" : "130.129.0.0/16", "type" : "CLIENT", },
    ]
